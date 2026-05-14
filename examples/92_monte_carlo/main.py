"""Monte Carlo Portfolio Simulator — Risk Analysis.

Runs Monte Carlo simulations on a portfolio using historical return
distributions. Outputs probability of loss, Value at Risk (VaR), and
expected range after N days. Pure stdlib — no numpy/scipy.

Usage:
    python3 main.py --symbols 'HK.00700,US.TCEHY,HK.00005'
                    --days 30 --simulations 10000
"""

import sys
import os
import logging
import argparse
import random
import math
import statistics
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connect import (
    create_quote_context,
    create_trade_context,
    clear_connection_cache,
)
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
DEFAULT_SYMBOLS = ["HK.00700", "US.TCEHY", "HK.00005"]
DEFAULT_DAYS = 30
DEFAULT_SIMULATIONS = 10000
DEFAULT_HISTORY_DAYS = 252  # 1 year of daily data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch_history(quote_ctx, code, num_days):
    """Fetch historical daily close prices with pagination."""
    closes = []
    start = ""
    while len(closes) < num_days + 10:
        need = num_days + 10 - len(closes)
        ret, df, next_page = quote_ctx.request_history_kline(
            code=code, start=start, num_bars=min(need, 50),
            ktype=ft.KLType.K_DAY,
        )
        if ret != ft.RetCode.SUCCESS:
            break
        if df is not None and not df.empty:
            closes.extend(df["close"].tolist())
        if not next_page:
            break
        start = next_page
    return closes[:num_days]


def compute_daily_returns(closes):
    """Compute daily log-returns from close prices."""
    returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] > 0:
            returns.append(math.log(closes[i] / closes[i - 1]))
    return returns


def get_current_positions(trd_ctx, quote_ctx, symbols):
    """Get current portfolio positions and market values."""
    positions = {}
    ret, df = trd_ctx.position_list_query(trd_env=ft.TrdEnv.SIMULATE)
    if ret == ft.RetCode.SUCCESS and df is not None and not df.empty:
        for _, row in df.iterrows():
            code = row.get("code", "")
            qty = float(row.get("qty", 0) or 0)
            if code in symbols and qty > 0:
                positions[code] = int(qty)

    # Get current prices
    prices = {}
    for code in symbols:
        ret, df = quote_ctx.get_stock_quote(code)
        if ret == ft.RetCode.SUCCESS and df is not None and not df.empty:
            prices[code] = float(df.iloc[-1]["last_price"])

    return positions, prices


def percentile(sorted_data, pct):
    """Compute percentile from sorted data using linear interpolation."""
    if not sorted_data:
        return 0
    k = (len(sorted_data) - 1) * pct / 100
    f = int(k)
    c = min(f + 1, len(sorted_data) - 1)
    if f == c:
        return sorted_data[f]
    return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


# ---------------------------------------------------------------------------
# Monte Carlo engine
# ---------------------------------------------------------------------------

def run_simulation(returns_by_asset, weights, initial_value, days, n_sims):
    """Run Monte Carlo simulation.

    Returns list of final portfolio values across all simulations.
    """
    n_assets = len(returns_by_asset)
    min_len = min(len(r) for r in returns_by_asset.values()) if returns_by_asset else 0

    if min_len < 5:
        logger.warning("Insufficient return data for simulation (%d min)", min_len)
        return []

    # Ensure all return series have the same length
    trimmed = {}
    for asset, rets in returns_by_asset.items():
        trimmed[asset] = rets[-min_len:]

    assets = sorted(trimmed.keys())
    return_matrix = [[trimmed[a][i] for a in assets] for i in range(min_len)]

    results = []
    for sim in range(n_sims):
        portfolio_value = initial_value
        for day in range(days):
            # Sample a random day from history
            idx = random.randint(0, len(return_matrix) - 1)
            daily_returns = return_matrix[idx]

            # Weighted portfolio return
            port_return = sum(
                w * daily_returns[i] for i, w in enumerate(weights)
            )
            portfolio_value *= (1 + port_return)

            # Stop if portfolio goes to zero or negative
            if portfolio_value <= 0:
                portfolio_value = 0
                break

        results.append(portfolio_value)

    return results


def format_distribution(results, initial_value):
    """Format simulation results into a summary."""
    if not results:
        return "No results"

    sorted_r = sorted(results)
    n = len(sorted_r)

    mean_val = statistics.mean(results)
    median_val = statistics.median(results)
    std_val = statistics.pstdev(results)

    var_5 = percentile(sorted_r, 5)
    var_1 = percentile(sorted_r, 1)
    pct_5 = percentile(sorted_r, 95)

    prob_loss = sum(1 for r in results if r < initial_value) / n * 100

    lines = []
    lines.append(f"  Simulations : {n:,}")
    lines.append(f"  Horizon     : {args.days} days")
    lines.append(f"  Initial     : ${initial_value:,.0f}")
    lines.append(f"  ─────────────────────────────────────")
    lines.append(f"  Mean        : ${mean_val:>12,.0f}  ({((mean_val/initial_value)-1)*100:>+.1f}%)")
    lines.append(f"  Median      : ${median_val:>12,.0f}  ({((median_val/initial_value)-1)*100:>+.1f}%)")
    lines.append(f"  Std Dev     : ${std_val:>12,.0f}")
    lines.append(f"  ─────────────────────────────────────")
    lines.append(f"  95th %%ile  : ${pct_5:>12,.0f}  (upside)")
    lines.append(f"  5th %%ile   : ${var_5:>12,.0f}  (downside)")
    lines.append(f"  1st %%ile   : ${var_1:>12,.0f}  (tail risk)")
    lines.append(f"  ─────────────────────────────────────")
    lines.append(f"  VaR (95%)   : ${initial_value - var_5:>12,.0f}  (potential loss)")
    lines.append(f"  VaR (99%)   : ${initial_value - var_1:>12,.0f}  (tail loss)")
    lines.append(f"  Prob Loss   : {prob_loss:>11.1f}%")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ASCII histogram
# ---------------------------------------------------------------------------

def render_histogram(results, initial_value, bins=30, width=50):
    """Render an ASCII histogram of final portfolio values."""
    if not results:
        return ""

    sorted_r = sorted(results)
    min_val = sorted_r[0]
    max_val = sorted_r[-1]
    bin_size = (max_val - min_val) / max(bins, 1)

    if bin_size <= 0:
        return ""

    # Count per bin
    counts = [0] * bins
    for val in results:
        idx = min(int((val - min_val) / bin_size), bins - 1)
        counts[idx] += 1

    max_count = max(counts) if counts else 1

    lines = []
    lines.append(f"\n  Distribution of outcomes ($)")
    lines.append(f"  Each █ ≈ {max(max_count // width, 1)} simulations")

    for i in range(bins):
        bin_start = min_val + i * bin_size
        bin_end = bin_start + bin_size
        bar_len = int(counts[i] / max_count * width) if max_count > 0 else 0
        bar = "█" * max(bar_len, 1) if counts[i] > 0 else ""
        marker = " ◂" if bin_start <= initial_value <= bin_end else ""
        lines.append(
            f"  ${bin_start:>12,.0f} │ {bar:<{width}}{marker}"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global args
    parser = argparse.ArgumentParser(description="Monte Carlo Portfolio Simulator")
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS),
                        help="Comma-separated stock symbols")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS,
                        help="Projection horizon in days (default 30)")
    parser.add_argument("--simulations", type=int, default=DEFAULT_SIMULATIONS,
                        help="Number of simulations (default 10000)")
    parser.add_argument("--history", type=int, default=DEFAULT_HISTORY_DAYS,
                        help="Lookback period for return data (default 252)")
    parser.add_argument("--equal-weight", action="store_true",
                        help="Use equal weights instead of market-cap weights")
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    n_days = args.days
    n_sims = args.simulations
    history_days = args.history

    if len(symbols) < 1:
        logger.error("Need at least one symbol.")
        return

    random.seed(42)  # reproducible results

    quote_ctx = create_quote_context()

    try:
        print(f"\n{'='*70}")
        print(f"  🎲 MONTE CARLO PORTFOLIO SIMULATOR")
        print(f"  Symbols : {', '.join(symbols)}")
        print(f"  Horizon : {n_days} days | Simulations : {n_sims:,}")
        print(f"{'='*70}")

        # ── Fetch historical data for each asset ────────────────────────
        all_returns = {}
        for sym in symbols:
            print(f"  Fetching {history_days} days of history for {sym} …")
            closes = fetch_history(quote_ctx, sym, history_days)
            if len(closes) < 20:
                logger.warning("Insufficient data for %s (%d bars) — skipping",
                               sym, len(closes))
                continue
            all_returns[sym] = compute_daily_returns(closes)
            print(f"    {len(all_returns[sym])} daily returns computed")

        if len(all_returns) < 2:
            logger.error("Need at least 2 assets with sufficient data.")
            return

        # ── Compute weights ─────────────────────────────────────────────
        assets = sorted(all_returns.keys())
        if args.equal_weight:
            weights = [1.0 / len(assets)] * len(assets)
        else:
            # Approximate by inverse volatility (lower vol = higher weight)
            vols = {}
            for a in assets:
                vols[a] = statistics.pstdev(all_returns[a])
            inv_vols = {a: 1.0 / max(v, 1e-10) for a, v in vols.items()}
            total = sum(inv_vols.values())
            weights = [inv_vols[a] / total for a in assets]

        print(f"\n  Portfolio weights:")
        for a, w in zip(assets, weights):
            vol = statistics.pstdev(all_returns[a]) * math.sqrt(252)
            print(f"    {a:<14} weight={w:>5.1%}  (ann. vol={vol:.1%})")

        # ── Initial portfolio value (normalised to $100,000) ────────────
        initial_value = 100_000.0

        # ── Run simulation ──────────────────────────────────────────────
        print(f"\n  Running {n_sims:,} simulations over {n_days} days …")
        results = run_simulation(all_returns, weights, initial_value,
                                 n_days, n_sims)

        if not results:
            logger.error("Simulation returned no results.")
            return

        # ── Results ─────────────────────────────────────────────────────
        print(format_distribution(results, initial_value, n_days))
        print(render_histogram(results, initial_value))

        # ── Percentile table ────────────────────────────────────────────
        print(f"\n  Key Percentiles:")
        for pct in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
            val = percentile(sorted(results), pct)
            pnl = val - initial_value
            print(f"    {pct:>3}%  →  ${val:>12,.0f}  (P&L: ${pnl:>+12,.0f})")

        print(f"\n{'='*70}\n")

    finally:
        quote_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()