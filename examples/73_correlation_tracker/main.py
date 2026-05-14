"""Multi-Asset Correlation Tracker — Real-time rolling Pearson correlation.

Subscribes to 10+ tickers in parallel, maintains rolling 60-bar return series,
computes a live correlation matrix, and flags pairs whose correlation has
spiked or collapsed.

Usage:
    python3 main.py [--window 60] [--min-bars 20]
"""

import sys
import os
import logging
import argparse
import math
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connect import create_quote_context, clear_connection_cache
import futu as ft

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DEFAULT_TICKERS = [
    "HK.00700", "HK.09988", "HK.03690", "HK.02318",
    "HK.00941", "HK.01024", "HK.02020", "HK.09618",
    "HK.03692", "HK.01810",
]
DEFAULT_WINDOW = 60
DEFAULT_MIN_BARS = 20
CORR_SPIKE_THRESHOLD = 0.3
TRD_ENV = ft.TrdEnv.SIMULATE

# ---------------------------------------------------------------------------
# Correlation engine (pure stdlib)
# ---------------------------------------------------------------------------

def pearson(x, y):
    """Pearson correlation coefficient. Returns None if undefined."""
    n = len(x)
    if n < 2:
        return None
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    dx = sum((xi - mx) ** 2 for xi in x)
    dy = sum((yi - my) ** 2 for yi in y)
    denom = (dx * dy) ** 0.5
    if denom < 1e-15:
        return None
    return num / denom


def correlation_matrix(series):
    """Compute correlation matrix for all pairs.

    series: dict {ticker: deque of log-returns}
    Returns: list of (ticker_a, ticker_b, correlation)
    """
    tickers = sorted(series.keys())
    pairs = []
    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            t1, t2 = tickers[i], tickers[j]
            # Align to same length
            min_len = min(len(series[t1]), len(series[t2]))
            if min_len < 2:
                continue
            x = list(series[t1])[-min_len:]
            y = list(series[t2])[-min_len:]
            r = pearson(x, y)
            pairs.append((t1, t2, r))
    return pairs


def log_return_series(series, baseline=20):
    """Compute rolling baseline correlations for spike detection."""
    tickers = sorted(series.keys())
    baseline_pairs = {}
    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            t1, t2 = tickers[i], tickers[j]
            s1, s2 = series[t1], series[t2]
            use_len = min(len(s1), len(s2), baseline)
            if use_len < 5:
                continue
            x = list(s1)[:use_len]
            y = list(s2)[:use_len]
            r = pearson(x, y)
            if r is not None:
                baseline_pairs[(t1, t2)] = r
    return baseline_pairs


# ---------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------

class ReturnCollector(ft.CurKlineHandlerBase):
    """Collects closing prices and computes log-returns per ticker."""

    def __init__(self, tickers, window=60, min_bars=20):
        super().__init__()
        self.tickers = tickers
        self.window = window
        self.min_bars = min_bars
        # price history: {ticker: deque of close prices}
        self.prices = {t: deque(maxlen=window + 1) for t in tickers}
        # return series: {ticker: deque of log-returns}
        self.returns = {t: deque(maxlen=window) for t in tickers}
        self.bar_count = {t: 0 for t in tickers}
        self.last_bars = {}  # latest close per ticker
        self.baseline = {}
        self.baseline_computed = False
        self.spike_alerts = deque(maxlen=10)

    def on_recv_rsp(self, rsp_pb):
        ret, content = super().on_recv_rsp(rsp_pb)
        if ret != ft.RetCode.SUCCESS:
            return ret, content

        code = content.get("code", "")
        if code not in self.tickers:
            return ret, content

        close = float(content.get("close", 0))
        if close <= 0:
            return ret, content

        self.prices[code].append(close)
        self.bar_count[code] += 1
        self.last_bars[code] = close

        # Compute log-return
        if len(self.prices[code]) >= 2:
            prev = self.prices[code][-2]
            if prev > 0:
                ret_val = math.log(close / prev)
                self.returns[code].append(ret_val)

        # Compute baseline once all tickers have enough bars
        if not self.baseline_computed:
            if all(self.bar_count[t] >= self.min_bars for t in self.tickers):
                self.baseline = log_return_series(self.returns, baseline=self.min_bars)
                self.baseline_computed = True
                logger.info("Baseline correlations computed. Live tracking started.")

        return ret, content

    def format_matrix(self):
        """Format correlation matrix as a text table."""
        # Build ticker list (only those with data)
        active = sorted([t for t in self.tickers if self.bar_count[t] >= 2])
        if len(active) < 2:
            return "  [need data from 2+ tickers]", active

        # Compute current correlations
        pairs = correlation_matrix(self.returns)
        pair_map = {}
        for t1, t2, r in pairs:
            pair_map[(t1, t2)] = r

        # Header
        lines = []
        col_w = 10
        header = " " * 12 + "".join(t.replace("HK.", "").rjust(col_w) for t in active)
        lines.append(header)

        for i, t1 in enumerate(active):
            row_label = t1.replace("HK.", "")[:10].rjust(12)
            cells = []
            for j, t2 in enumerate(active):
                if i == j:
                    cells.append(" ".rjust(col_w))
                elif i < j:
                    r = pair_map.get((t1, t2))
                    if r is not None:
                        cell = f"{r:+.3f}"
                    else:
                        cell = "   N/A  "
                    cells.append(cell.rjust(col_w))
                else:
                    cells.append("".rjust(col_w))
            lines.append(row_label + "".join(cells))

        return "\n".join(lines), active

    def get_spike_alerts(self, current_pairs):
        """Compare current correlations to baseline and flag spikes."""
        if not self.baseline:
            return []

        alerts = []
        for (t1, t2), baseline_r in self.baseline.items():
            key = (t1, t2) if (t1, t2) in current_pairs else (t2, t1)
            current = current_pairs.get(key)
            if current is None:
                continue
            delta = abs(current - baseline_r)
            if delta > CORR_SPIKE_THRESHOLD:
                direction = "↑" if current > baseline_r else "↓"
                alerts.append(
                    f"  {direction} {t1} ↔ {t2}: {baseline_r:+.3f} → {current:+.3f} "
                    f"({delta:+.3f})"
                )
        return alerts


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Multi-asset correlation tracker")
    parser.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS,
                        help="Space-separated ticker list")
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW,
                        help="Rolling return window (default 60)")
    parser.add_argument("--min-bars", type=int, default=DEFAULT_MIN_BARS,
                        help="Min bars before tracking starts (default 20)")
    args = parser.parse_args()

    tickers = args.tickers
    window = args.window
    min_bars = args.min_bars

    quote_ctx = create_quote_context()
    collector = ReturnCollector(tickers, window=window, min_bars=min_bars)

    try:
        ret, _ = quote_ctx.subscribe(
            code_list=tickers,
            subtype_list=[ft.SubType.CUR_KLINE],
            is_first_push=True,
        )
        if ret != ft.RetCode.SUCCESS:
            logger.error("subscribe failed: %s", ret)
            return
        quote_ctx.set_handler(collector)
        logger.info("Subscribed to CUR_KLINE for %d tickers", len(tickers))

        last_bar_counts = {t: 0 for t in tickers}
        last_display = 0

        import time as _time

        print("\n" + "=" * 70)
        print(f"  CORRELATION TRACKER — {len(tickers)} tickers, window={window}")
        print("=" * 70)

        while True:
            _time.sleep(5)

            # Check for new bars
            any_new = any(
                collector.bar_count[t] != last_bar_counts[t]
                for t in tickers
            )
            if not any_new:
                continue
            last_bar_counts = dict(collector.bar_counts) if hasattr(collector, 'bar_counts') else dict(collector.bar_count)

            now = _time.time()
            if now - last_display < 30:
                continue
            last_display = now

            # Matrix
            matrix_str, active = collector.format_matrix()
            print(f"\n[{_time.strftime('%H:%M:%S')}] Correlation Matrix ({len(active)} active)")
            print(matrix_str)

            # Spike alerts
            # Build current pair map for alert comparison
            pairs = correlation_matrix(collector.returns)
            current_map = {}
            for t1, t2, r in pairs:
                if r is not None:
                    current_map[(t1, t2)] = r

            alerts = collector.get_spike_alerts(current_map)
            if alerts:
                print(f"\n  ⚡ CORRELATION SPIKES (Δ > {CORR_SPIKE_THRESHOLD:.1f}):")
                for a in alerts:
                    print(a)
            else:
                print(f"\n  ✓ No significant correlation changes detected.")

            # Progress bar for each ticker
            warmup = [f"{t}: {collector.bar_count[t]}/{min_bars}"
                      for t in tickers
                      if collector.bar_count[t] < min_bars]
            if warmup:
                print(f"  Warming up: {', '.join(warmup)}")

    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    finally:
        quote_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()