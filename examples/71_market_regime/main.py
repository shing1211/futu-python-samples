"""Market Regime Detector — ADX + Volatility classification.

Computes ADX and rolling volatility from live K-lines to classify market
regime: TRENDING, RANGING, or HIGH-VOL BREAKOUT.

Usage:
    python3 main.py [--stock HK.00700] [--period 14] [--window 100]
"""

import sys
import logging
import argparse
from collections import deque
import statistics

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

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
DEFAULT_STOCK = "HK.00700"
DEFAULT_ADX_PERIOD = 14
DEFAULT_WINDOW = 100
TRD_ENV = ft.TrdEnv.SIMULATE

# Regime thresholds
ADX_TRENDING = 25
ADX_RANGING = 20
DI_RATIO_THRESHOLD = 1.3
VOL_BREAKOUT_MULT = 2.0


# ---------------------------------------------------------------------------
# ADX computation (pure stdlib)
# ---------------------------------------------------------------------------

def tr(dm_plus, dm_minus, high, low, close_prev):
    """True Range and Directional Movement for one bar."""
    tr_val = max(
        high - low,
        abs(high - close_prev),
        abs(low - close_prev),
    )
    # +DM
    diff_up = high - dm_plus[1] if dm_plus[1] is not None else 0
    diff_down = dm_minus[1] - low if dm_minus[1] is not None else 0
    if diff_up > diff_down and diff_up > 0:
        dm_plus_val = diff_up
    else:
        dm_plus_val = 0
    # -DM
    if diff_down > diff_up and diff_down > 0:
        dm_minus_val = diff_down
    else:
        dm_minus_val = 0
    return tr_val, dm_plus_val, dm_minus_val


def compute_adx(bars, period=14):
    """
    Compute ADX, DI+, DI- from a list of bars.
    Each bar: {"high": float, "low": float, "close": float}
    Returns (adx, di_plus, di_minus) or (None, None, None) if insufficient data.
    """
    n = len(bars)
    if n < period + 1:
        return None, None, None

    tr_vals = []
    dm_plus_vals = []
    dm_minus_vals = []

    for i in range(1, n):
        t, dp, dm = tr(
            bars[i]["high"], bars[i]["low"], bars[i]["close"],
            bars[i - 1]["close"],
        )
        tr_vals.append(t)
        dm_plus_vals.append(dp)
        dm_minus_vals.append(dm)

    # Wilder smoothing: first avg = simple mean of first `period` values
    def wilder_smooth(values, period):
        result = []
        if len(values) < period:
            return result
        avg = sum(values[:period]) / period
        result.append(avg)
        for v in values[period:]:
            avg = (avg * (period - 1) + v) / period
            result.append(avg)
        return result

    smoothed_tr = wilder_smooth(tr_vals, period)
    smoothed_dp = wilder_smooth(dm_plus_vals, period)
    smoothed_dm = wilder_smooth(dm_minus_vals, period)

    if not smoothed_tr or smoothed_tr[-1] == 0:
        return 0, 0, 0

    di_plus = 100 * smoothed_dp[-1] / smoothed_tr[-1]
    di_minus = 100 * smoothed_dm[-1] / smoothed_tr[-1]

    dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus) if (di_plus + di_minus) > 0 else 0

    # Smooth DX to get ADX
    if len(smoothed_tr) >= 2:
        # Use last few DX values for smoothing
        dx_series = []
        for i in range(len(smoothed_tr)):
            dp_i = smoothed_dp[i]
            dm_i = smoothed_dm[i]
            tr_i = smoothed_tr[i]
            di_p = 100 * dp_i / tr_i if tr_i > 0 else 0
            di_m = 100 * dm_i / tr_i if tr_i > 0 else 0
            denom = di_p + di_m
            dx_series.append(100 * abs(di_p - di_m) / denom if denom > 0 else 0)
        adx = sum(dx_series[-period:]) / min(period, len(dx_series))
    else:
        adx = dx

    return adx, di_plus, di_minus


def compute_rolling_vol(bars, window=20):
    """Annualised realised volatility (coefficient of variation × sqrt(252))."""
    if len(bars) < window:
        return None
    closes = [b["close"] for b in bars[-window:]]
    if len(closes) < 2:
        return None
    returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] > 0:
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
    if len(returns) < 2:
        return None
    vol = statistics.pstdev(returns) * (252 ** 0.5)  # annualised
    return vol


def classify_regime(adx, di_plus, di_minus, vol, median_vol):
    """Classify current market regime."""
    if adx is None or vol is None:
        return "WARMUP"

    di_ratio = max(di_plus, di_minus) / min(di_plus, di_minus) if min(di_plus, di_minus) > 0 else 0

    # Trending: ADX > 25 and DI ratio > threshold
    if adx > ADX_TRENDING and di_ratio > DI_RATIO_THRESHOLD:
        trend_dir = "▲ BULL" if di_plus > di_minus else "▼ BEAR"
        return f"TRENDING {trend_dir}"

    # Ranging: ADX < 20
    if adx < ADX_RANGING:
        return "RANGING 😴"

    # High-vol breakout: ADX rising and vol > 2× median
    if vol > VOL_BREAKOUT_MULT * median_vol and adx > ADX_RANGING:
        return "⚡ BREAKOUT"

    # Transition zone
    if di_plus > di_minus:
        return "TRANSITION ▲"
    else:
        return "TRANSITION ▼"


# ---------------------------------------------------------------------------
# Bar collector via subscribe
# ---------------------------------------------------------------------------

class BarCollector(ft.CurKlineHandlerBase):
    """Collects K-line bars via push subscription."""

    def __init__(self, maxlen=200):
        super().__init__()
        self.bars = deque(maxlen=maxlen)

    def on_recv_rsp(self, rsp_pb):
        ret, content = super().on_recv_rsp(rsp_pb)
        if ret != ft.RetCode.SUCCESS:
            return ret, content
        code = content.get("code", "")
        ktype = content.get("ktype", "")
        close = content.get("close", 0)
        high = content.get("high", 0)
        low = content.get("low", 0)
        timestamp = content.get("timestamp", 0)
        self.bars.append({
            "code": code,
            "ktype": ktype,
            "close": float(close),
            "high": float(high),
            "low": float(low),
            "timestamp": timestamp,
        })
        return ret, content


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def fetch_initial_bars(quote_ctx, code, num):
    """Fetch historical bars for warmup."""
    bars = []
    next_token = ""
    while len(bars) < num:
        need = num - len(bars)
        ret, df, next_token = quote_ctx.request_history_kline(
            code=code, start=next_token, num_bars=min(need, 50),
            ktype=ft.KLType.K_DAY,
        )
        if ret != ft.RetCode.SUCCESS:
            logger.error("request_history_kline failed: %s", ret)
            break
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                bars.append({
                    "close": float(row["close"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                })
        if not next_token:
            break
    return bars


def main():
    parser = argparse.ArgumentParser(description="Market Regime Detector (ADX + Vol)")
    parser.add_argument("--stock", default=DEFAULT_STOCK, help="Stock code")
    parser.add_argument("--period", type=int, default=DEFAULT_ADX_PERIOD,
                        help="ADX period (default 14)")
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW,
                        help="Rolling window size (default 100)")
    args = parser.parse_args()

    code = args.stock
    period = args.period
    vol_window = args.window

    quote_ctx = create_quote_context()

    try:
        # ── Bootstrap ──────────────────────────────────────────────────
        logger.info("Fetching initial bars for %s …", code)
        hist_bars = fetch_initial_bars(quote_ctx, code, vol_window)
        logger.info("Loaded %d historical bars.", len(hist_bars))

        vol_history = deque(maxlen=60)  # for median vol baseline

        # ── Set up push subscription ───────────────────────────────────
        handler = BarCollector()
        ret, _ = quote_ctx.subscribe(
            code_list=[code],
            subtype_list=[ft.SubType.CUR_KLINE],
            is_first_push=True,
        )
        if ret != ft.RetCode.SUCCESS:
            logger.error("subscribe failed: %s", ret)
            return
        quote_ctx.set_handler(handler)
        logger.info("Subscribed to CUR_KLINE for %s", code)

        print("\n" + "=" * 50)
        print(f"  MARKET REGIME DETECTOR — {code}")
        print(f"  ADX period={period}  vol_window={vol_window}")
        print("=" * 50)

        # ── Live loop ──────────────────────────────────────────────────
        import time as _time

        last_print = 0
        while True:
            _time.sleep(5)

            # Merge historical + live bars
            all_bars = list(hist_bars) + list(handler.bars)
            if len(all_bars) < period + 1:
                remaining = period + 1 - len(all_bars)
                logger.info("Warming up … %d / %d bars", len(all_bars), period + 1)
                continue

            # Compute indicators
            adx, di_p, di_m = compute_adx(all_bars, period=period)
            vol = compute_rolling_vol(all_bars, window=min(60, len(all_bars)))

            if vol is not None:
                vol_history.append(vol)
            median_vol = statistics.median(vol_history) if vol_history else 1.0

            regime = classify_regime(adx, di_p, di_m, vol, median_vol)

            # Throttle print to every 30s
            now = _time.time()
            if now - last_print >= 30 or "BREAKOUT" in regime:
                last_print = now
                n_bars = len(all_bars)
                print(
                    f"[{_time.strftime('%H:%M:%S')}] bars={n_bars:>4}  "
                    f"ADX={adx:>6.1f}  DI+= {di_p:>5.1f}  DI-={di_m:>5.1f}  "
                    f"Vol={vol:>6.2f}  Med={median_vol:>6.2f}  → {regime}"
                )

            # Keep historical window bounded
            if len(hist_bars) > vol_window:
                hist_bars = hist_bars[-vol_window:]

    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    finally:
        quote_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()