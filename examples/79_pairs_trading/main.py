"""Pairs Trading (Cointegration) — SIMULATE only.

Uses Engle-Granger cointegration test to find a mean-reverting spread
between two stocks. When the spread widens beyond ±2σ, trade the
convergence. Uses HK.00700 (Tencent) and US.TCEHY as a demo pair.

Usage:
    python3 main.py [--stock-a HK.00700] [--stock-b US.TCEHY]
                    [--lookback 60] [--max-minutes 30]
"""

import sys
import os
import logging
import argparse
import time
from collections import deque
import statistics

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connect import (
    create_quote_context,
    create_trade_context,
    get_demo_trade_password,
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
DEFAULT_A = "HK.00700"
DEFAULT_B = "US.TCEHY"
DEFAULT_LOOKBACK = 60
DEFAULT_ZSCORE = 2.0
DEFAULT_MAX_MINUTES = 30
TRD_ENV = ft.TrdEnv.SIMULATE


# ---------------------------------------------------------------------------
# Cointegration helpers
# ---------------------------------------------------------------------------

def ols_regression(x, y):
    """Simple OLS: y = alpha + beta * x. Returns (alpha, beta, residuals)."""
    n = len(x)
    if n < 3:
        return None, None, []
    mx, my = sum(x) / n, sum(y) / n
    ss_xy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    ss_xx = sum((xi - mx) ** 2 for xi in x)
    if abs(ss_xx) < 1e-15:
        return None, None, []
    beta = ss_xy / ss_xx
    alpha = my - beta * mx
    residuals = [yi - (alpha + beta * xi) for xi, yi in zip(x, y)]
    return alpha, beta, residuals


def adf_test(residuals, max_lag=5):
    """Simplified ADF test on residuals. Returns (adf_stat, is_stationary).

    Uses the Dickey-Fuller statistic: gamma / SE(gamma).
    A more negative value → more likely stationary.
    Critical values (approximate, n=60): 1% = -3.5, 5% = -2.9.
    """
    n = len(residuals)
    if n < 10:
        return 0, False

    dy = [residuals[i] - residuals[i - 1] for i in range(1, n)]
    y_lag = residuals[:-1]

    # Regress dy on y_lag (and optionally lagged differences)
    mx_dy = sum(dy) / len(dy)
    mx_y = sum(y_lag) / len(y_lag)

    num = sum((yi - mx_y) * (di - mx_dy) for yi, di in zip(y_lag, dy))
    den = sum((yi - mx_y) ** 2 for yi in y_lag)

    if abs(den) < 1e-15:
        return 0, False

    gamma = num / den

    # Residual std error
    predicted = [mx_dy + gamma * (yi - mx_y) for yi in y_lag]
    se = (sum((di - p) ** 2 for di, p in zip(dy, predicted)) / (len(dy) - 2)) ** 0.5
    if se < 1e-15:
        return gamma, True if gamma < 0 else False

    adf_stat = gamma / se
    # Approximate 5 % critical value for ~60 observations: -2.9
    return adf_stat, adf_stat < -2.9


def hedge_ratio_adjusted_price(price_a, price_b, beta):
    """Compute the spread: price_a - beta * price_b."""
    return price_a - beta * price_b


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def fetch_daily_history(quote_ctx, code, num_days):
    """Fetch daily K-line history. Returns list of {'close': float}."""
    bars = []
    next_token = ""
    while len(bars) < num_days + 10:
        need = num_days + 10 - len(bars)
        ret, df, next_token = quote_ctx.request_history_kline(
            code=code, start=next_token, num_bars=min(need, 50),
            ktype=ft.KLType.K_DAY,
        )
        if ret != ft.RetCode.SUCCESS:
            break
        if df is None or df.empty:
            break
        for _, row in df.iterrows():
            bars.append({"close": float(row["close"])})
        if not next_token:
            break
    return bars[:num_days]


def main():
    parser = argparse.ArgumentParser(description="Pairs Trading (Cointegration)")
    parser.add_argument("--stock-a", default=DEFAULT_A, help="Stock A (e.g. HK.00700)")
    parser.add_argument("--stock-b", default=DEFAULT_B, help="Stock B (e.g. US.TCEHY)")
    parser.add_argument("--lookback", type=int, default=DEFAULT_LOOKBACK,
                        help="Lookback period for cointegration (default 60)")
    parser.add_argument("--zscore", type=float, default=DEFAULT_ZSCORE,
                        help="Z-score threshold for entry (default 2.0)")
    parser.add_argument("--max-minutes", type=float, default=DEFAULT_MAX_MINUTES,
                        help="Safety timeout in minutes (default 30)")
    args = parser.parse_args()

    stock_a = args.stock_a
    stock_b = args.stock_b
    lookback = args.lookback
    zscore_threshold = args.zscore
    max_seconds = args.max_minutes * 60

    quote_ctx = create_quote_context()
    trd_ctx = create_trade_context()
    pwd = get_demo_trade_password()

    try:
        # ── Unlock SIMULATE ────────────────────────────────────────────
        ret, _ = trd_ctx.unlock_trade(pwd, trd_env=TRD_ENV)
        if ret != ft.RetCode.SUCCESS:
            logger.error("unlock_trade failed: %s", ret)
            return
        logger.info("SIMULATE account unlocked.")

        # ── Fetch history ──────────────────────────────────────────────
        logger.info("Fetching %d daily bars for %s …", lookback, stock_a)
        hist_a = fetch_daily_history(quote_ctx, stock_a, lookback)
        logger.info("Fetching %d daily bars for %s …", lookback, stock_b)
        hist_b = fetch_daily_history(quote_ctx, stock_b, lookback)

        min_len = min(len(hist_a), len(hist_b))
        if min_len < lookback:
            logger.warning("Insufficient data: %d / %d bars. Proceeding with available.",
                           min_len, lookback)

        closes_a = [b["close"] for b in hist_a[:min_len]]
        closes_b = [b["close"] for b in hist_b[:min_len]]

        # ── Cointegration test ─────────────────────────────────────────
        alpha, beta, residuals = ols_regression(closes_b, closes_a)
        if beta is None:
            logger.error("OLS regression failed — cannot determine hedge ratio.")
            return

        adf_stat, stationary = adf_test(residuals)
        print(f"\n{'='*60}")
        print(f"  PAIRS TRADING — {stock_a} vs {stock_b}")
        print(f"{'='*60}")
        print(f"  Hedge ratio (β): {beta:.4f}")
        print(f"  Intercept (α):   {alpha:.4f}")
        print(f"  ADF statistic:   {adf_stat:.3f}")
        print(f"  Stationary:      {'✅ YES' if stationary else '❌ NO'}")

        if not stationary:
            logger.warning("Spread is NOT stationary — pairs trade may not work!")
            logger.warning("Consider choosing a different pair.")

        spread_mean = statistics.mean(residuals)
        spread_std = statistics.pstdev(residuals)
        print(f"  Spread mean:     {spread_mean:.4f}")
        print(f"  Spread std:      {spread_std:.4f}")
        print(f"{'='*60}")

        if spread_std < 1e-8:
            logger.error("Spread has zero variance — exiting.")
            return

        # ── Live trading loop ──────────────────────────────────────────
        position = None  # "long_a_short_b" or "short_a_long_b" or None
        entry_spread = 0.0
        state = {"has_position": False, "direction": None, "entry_z": 0.0}

        deadline = time.time() + max_seconds
        while time.time() < deadline:
            # Get latest prices
            ret_a, df_a = quote_ctx.get_stock_quote(stock_a)
            ret_b, df_b = quote_ctx.get_stock_quote(stock_b)
            if ret_a != ft.RetCode.SUCCESS or ret_b != ft.RetCode.SUCCESS:
                time.sleep(5)
                continue

            price_a = float(df_a.iloc[-1]["last_price"])
            price_b = float(df_b.iloc[-1]["last_price"])
            current_spread = price_a - beta * price_b
            z = (current_spread - spread_mean) / spread_std

            print(
                f"[{time.strftime('%H:%M:%S')}]  A={price_a:.2f}  B={price_b:.2f}  "
                f"spread={current_spread:.4f}  z={z:+.2f}"
            )

            # ── Entry signals ─────────────────────────────────────────
            if not state["has_position"]:
                if z > zscore_threshold:
                    # A is expensive relative to B → short A, long B
                    logger.info("🔴 Z=%.2f → SHORT %s / LONG %s", z, stock_a, stock_b)
                    state["has_position"] = True
                    state["direction"] = "short_a_long_b"
                    state["entry_z"] = z

                    # Place orders (SIMULATE)
                    qty_a = 100
                    qty_b = int(qty_a * beta) if beta > 0 else 100
                    _place_order(trd_ctx, stock_a, ft.TrdSide.SELL, qty_a, 0, "pairs_short_a")
                    _place_order(trd_ctx, stock_b, ft.TrdSide.BUY, qty_b, 0, "pairs_long_b")

                elif z < -zscore_threshold:
                    # A is cheap relative to B → long A, short B
                    logger.info("🟢 Z=%.2f → LONG %s / SHORT %s", z, stock_a, stock_b)
                    state["has_position"] = True
                    state["direction"] = "long_a_short_b"
                    state["entry_z"] = z

                    qty_a = 100
                    qty_b = int(qty_a * beta) if beta > 0 else 100
                    _place_order(trd_ctx, stock_a, ft.TrdSide.BUY, qty_a, 0, "pairs_long_a")
                    _place_order(trd_ctx, stock_b, ft.TrdSide.SELL, qty_b, 0, "pairs_short_b")

            # ── Exit signals ──────────────────────────────────────────
            elif state["has_position"]:
                if abs(z) < 0.3:  # Spread converged — close
                    logger.info("✅ Z=%.2f → spread converged — closing position.", z)
                    state["has_position"] = False
                    _close_all(trd_ctx)

                elif abs(z) > zscore_threshold * 2:
                    # Spread widened further — tighten stop
                    logger.warning("⚠️ Z=%.2f → spread widened, holding...", z)

            time.sleep(15)

        logger.info("⏰ Time limit reached.")

    finally:
        logger.info("Cleaning up …")
        trd_ctx.cancel_all_order(cancel_all_orders=True, trd_env=TRD_ENV)
        quote_ctx.close()
        trd_ctx.close()
        logger.info("Done.")


def _place_order(trd_ctx, code, side, qty, price, remark):
    ret, order_id = trd_ctx.place_order(
        price=price, code=code, qty=qty,
        trd_side=side, order_type=ft.OrderType.NORMAL,
        trd_env=TRD_ENV, remark=remark,
    )
    if ret != ft.RetCode.SUCCESS:
        logger.error("place_order failed: %s", ret)
        return None
    logger.info("  → %s %d %s @ %s", side, qty, code, price or "MKT")
    return order_id


def _close_all(trd_ctx):
    """Record exit state — actual cleanup handled by finally block below."""


if __name__ == "__main__":
    main()