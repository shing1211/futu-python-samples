"""Bollinger Band Bounce — SIMULATE only.

Computes 20-period Bollinger Bands using pure stdlib statistics.
Enters a mean-reversion trade when price crosses ±2σ from the mean.

Usage:
    python3 main.py <stock_code> [--period 20] [--stdev 2.0]
"""

import sys
import os
import logging
import time
import argparse
import statistics
from collections import deque
from datetime import datetime

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
DEFAULT_STOCK = "HK.00700"
DEFAULT_PERIOD = 20
DEFAULT_ZSCORE = 2.0
DEFAULT_MAX_MINUTES = 10
TRD_ENV = ft.TrdEnv.SIMULATE

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch_history_kline(quote_ctx, code, num_bars):
    """Fetch historical klines, handling pagination. Returns list of dicts."""
    bars = []
    next_token = None
    while len(bars) < num_bars + 5:
        ret, df, next_token = quote_ctx.request_history_kline(
            code=code,
            start=next_token if next_token else "",
            num_bars=num_bars + 5 - len(bars),
            ktype=ft.KLType.K_DAY,
        )
        if ret != ft.RetCode.SUCCESS:
            logger.error("request_history_kline failed: %s", ret)
            return bars
        records = df.to_dict("records")
        bars.extend(records)
        if not next_token:
            break
    return bars[:num_bars]


def get_current_kline_snapshot(quote_ctx, code):
    """Get the current (unfinished) bar."""
    ret, df = quote_ctx.get_cur_kline(code=code, ktype=ft.KLType.K_DAY, num=1)
    if ret != ft.RetCode.SUCCESS:
        return None
    return df.iloc[-1].to_dict()


def place_market_order(trd_ctx, code, direction, qty):
    """Place a market order and return order ID."""
    ret, order_id = trd_ctx.place_order(
        price=0,
        code=code,
        qty=qty,
        trd_side=direction,
        order_type=ft.OrderType.NORMAL,
        trd_env=TRD_ENV,
    )
    if ret != ft.RetCode.SUCCESS:
        logger.error("place_order failed: %s", ret)
        return None
    logger.info("Order placed → %s  direction=%s  qty=%d", order_id, direction, qty)
    return order_id


def place_stop_order(trd_ctx, code, direction, qty, stop_price):
    """Place a stop order."""
    ret, order_id = trd_ctx.place_order(
        price=stop_price,
        code=code,
        qty=qty,
        trd_side=direction,
        order_type=ft.OrderType.STOP,
        trd_env=TRD_ENV,
    )
    if ret != ft.RetCode.SUCCESS:
        logger.error("place_stop_order failed: %s", ret)
        return None
    return order_id


def cancel_all(trd_ctx):
    """Cancel all open orders."""
    ret, _ = trd_ctx.cancel_all_order(cancel_all_orders=True, trd_env=TRD_ENV)
    if ret != ft.RetCode.SUCCESS:
        logger.warning("cancel_all_order returned: %s", ret)


def compute_bollinger(price_window, period, zscore):
    """Compute Bollinger Bands from a window of close prices.

    Returns (upper, middle, lower) or (None, None, None) if insufficient data.
    """
    if len(price_window) < period:
        return None, None, None
    recent = list(price_window)[-period:]
    mean = statistics.mean(recent)
    std = statistics.pstdev(recent)
    if std < 1e-8:  # flat market
        return mean, mean, mean
    upper = mean + zscore * std
    lower = mean - zscore * std
    return upper, mean, lower

# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------
IDLE = "IDLE"
ENTERED = "ENTERED"
EXITING = "EXITING"

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Bollinger Band mean reversion")
    parser.add_argument("code", nargs="?", default=DEFAULT_STOCK)
    parser.add_argument("--period", type=int, default=DEFAULT_PERIOD,
                        help="Bollinger period (default 20)")
    parser.add_argument("--stdev", type=float, default=DEFAULT_ZSCORE,
                        help="Number of std devs for bands (default 2.0)")
    parser.add_argument("--max-minutes", type=float, default=DEFAULT_MAX_MINUTES,
                        help="Safety timeout in minutes (default 10)")
    args = parser.parse_args()

    code = args.code
    period = args.period
    zscore = args.stdev
    max_seconds = args.max_minutes * 60
    deadline = time.time() + max_seconds

    quote_ctx = create_quote_context()
    trd_ctx = create_trade_context()

    state = IDLE
    position_qty = 0
    entry_price = 0.0
    stop_order_id = None

    # Rolling window of close prices
    close_window = deque(maxlen=period * 3)  # keep 3× period for context

    try:
        # ── Bootstrap historical data ──────────────────────────────────
        logger.info("Fetching %d historical daily bars for %s …", period * 2, code)
        bars = fetch_history_kline(quote_ctx, code, period * 2)
        for b in bars:
            close_window.append(b["close"])
        logger.info("Loaded %d bars. Need %d before first signal.", len(close_window), period)

        # ── Main loop ──────────────────────────────────────────────────
        while time.time() < deadline:
            # Get latest bar
            cur = get_current_kline_snapshot(quote_ctx, code)
            if cur is None:
                time.sleep(5)
                continue

            close_price = cur["close"]
            close_window.append(close_price)

            upper, middle, lower = compute_bollinger(close_window, period, zscore)
            if upper is None:
                remaining = period - len(close_window)
                logger.info("Warming up … %d / %d bars", len(close_window), period)
                time.sleep(10)
                continue

            # ── State machine ──────────────────────────────────────────
            if state == IDLE:
                z = (close_price - middle) / (upper - middle) * zscore if upper != middle else 0
                # Long when price drops below lower band
                if close_price <= lower:
                    logger.info("🟢 LONG signal: price %.2f ≤ lower %.2f (z=%.2f)", close_price, lower, z)
                    qty = 100
                    order_id = place_market_order(trd_ctx, code, ft.TrdSide.BUY, qty)
                    if order_id:
                        state = ENTERED
                        position_qty = qty
                        entry_price = close_price
                        # Place stop at middle band
                        stop_order_id = place_stop_order(
                            trd_ctx, code, ft.TrdSide.SELL, qty, middle,
                        )
                        logger.info("Position opened at %.2f  stop=%.2f", entry_price, middle)

                # Short when price rises above upper band (if your account supports shorting)
                elif close_price >= upper:
                    logger.info("🔴 SHORT signal (SIMULATE): price %.2f ≥ upper %.2f", close_price, upper)
                    # Shorting depends on market rules; here we just log
                    # For HK stocks in SIMULATE, short may not be available
                    logger.info("Shorting not demonstrated — skipping (would need margin account)")

                else:
                    logger.info(
                        "ℹ️ No signal: price=%.2f  lower=%.2f  mid=%.2f  upper=%.2f",
                        close_price, lower, middle, upper,
                    )

            elif state == ENTERED:
                # Check if stop was hit
                if stop_order_id:
                    # Verify order status
                    ret, orders = trd_ctx.order_list_query(trd_env=TRD_ENV)
                    if ret == ft.RetCode.SUCCESS:
                        filled = False
                        for _, row in orders.iterrows():
                            if row["order_id"] == stop_order_id:
                                status = row["order_status"]
                                if status in (ft.OrderStatus.FILLED_ALL, ft.OrderStatus.CANCELLED_ALL):
                                    filled = True
                                    break
                        if filled:
                            logger.warning("🛑 Stop hit! Exiting position.")
                            state = IDLE
                            position_qty = 0
                            stop_order_id = None

                # Trail stop: move to middle band if price goes past it
                if close_price >= entry_price and stop_order_id:
                    new_stop = entry_price  # breakeven
                    logger.info("📈 Price above entry %.2f → moving stop to breakeven %.2f",
                                close_price, new_stop)
                    # (Simplified: just log; full trail would cancel/re-place)

            else:  # EXITING
                logger.info("Exiting position …")
                state = IDLE

            time.sleep(15)  # check every 15 seconds

        logger.info("⏰ Time limit reached.")

    finally:
        logger.info("Cleaning up …")
        cancel_all(trd_ctx)
        quote_ctx.close()
        trd_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()