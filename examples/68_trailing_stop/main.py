"""Trailing Stop Execution — SIMULATE only.

Demonstrates a trailing stop-loss that follows the price favorably.
When price moves up, the stop tightens. When price hits the stop, we exit.

Usage:
    python3 main.py <stock_code> [--trail-pct 0.02] [--max-minutes 5]
"""

import sys
import logging
import time
import argparse

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

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
DEFAULT_TRAIL_PCT = 0.02        # 2 % trail width
DEFAULT_MAX_MINUTES = 5         # safety timeout
TRD_ENV = ft.TrdEnv.SIMULATE

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_last_price(quote_ctx, code):
    """Return the last price for *code*, or None on failure."""
    ret, df = quote_ctx.get_stock_quote(code)
    if ret != ft.RetCode.SUCCESS:
        logger.warning("get_stock_quote(%s) failed: %s", code, ret)
        return None
    return df.iloc[-1]["last_price"]


def place_initial_order(trd_ctx, code, direction, qty, remark="trailing-stop entry"):
    """Place a market order and return the order ID (or None)."""
    ret, order_id = trd_ctx.place_order(
        price=0,                          # market order
        code=code,
        qty=qty,
        trd_side=direction,
        order_type=ft.OrderType.NORMAL,
        trd_env=TRD_ENV,
        remark=remark,
    )
    if ret != ft.RetCode.SUCCESS:
        logger.error("place_order failed: %s", ret)
        return None
    logger.info("Order placed → %s  qty=%d", order_id, qty)
    return order_id


def place_stop_order(trd_ctx, code, direction, qty, stop_price, remark="trailing-stop"):
    """Place a stop order and return the order ID (or None)."""
    ret, order_id = trd_ctx.place_order(
        price=stop_price,
        code=code,
        qty=qty,
        trd_side=direction,
        order_type=ft.OrderType.STOP,
        trd_env=TRD_ENV,
        remark=remark,
    )
    if ret != ft.RetCode.SUCCESS:
        logger.error("place_stop_order failed: %s", ret)
        return None
    logger.info("Stop order placed → %s  stop=%.2f", order_id, stop_price)
    return order_id


def cancel_order(trd_ctx, order_id):
    """Cancel a single order. Returns True on success."""
    if not order_id:
        return True
    ret, _ = trd_ctx.cancel_order(order_id, trd_env=TRD_ENV)
    if ret != ft.RetCode.SUCCESS:
        logger.warning("cancel_order(%s) failed: %s", order_id, ret)
        return False
    logger.info("Order %s cancelled", order_id)
    return True


def is_position_closed(trd_ctx, order_id):
    """Check whether *order_id* has been fully filled or cancelled."""
    ret, orders = trd_ctx.order_list_query(trd_env=TRD_ENV)
    if ret != ft.RetCode.SUCCESS:
        return False
    for _, row in orders.iterrows():
        if row["order_id"] == order_id:
            status = row["order_status"]
            if status in (ft.OrderStatus.FILLED_ALL, ft.OrderStatus.CANCELLED_ALL):
                return True
    return False

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Trailing stop demo")
    parser.add_argument("code", nargs="?", default=DEFAULT_STOCK, help="Stock code")
    parser.add_argument("--trail-pct", type=float, default=DEFAULT_TRAIL_PCT,
                        help="Trail width as fraction of price (default 0.02)")
    parser.add_argument("--max-minutes", type=float, default=DEFAULT_MAX_MINUTES,
                        help="Maximum runtime in minutes (default 5)")
    args = parser.parse_args()

    code = args.code
    trail_pct = args.trail_pct
    max_seconds = args.max_minutes * 60
    min_tick_move = 0.01  # minimum price move to reissue stop (avoid thrashing)

    quote_ctx = create_quote_context()
    trd_ctx = create_trade_context()
    deadline = time.time() + max_seconds

    try:
        # ── Pre-flight ────────────────────────────────────────────────
        price = get_last_price(quote_ctx, code)
        if price is None:
            logger.error("Cannot fetch price for %s — exiting.", code)
            return
        logger.info("Current price for %s: %.2f", code, price)

        # ── Enter a long position ─────────────────────────────────────
        qty = 100  # demo quantity
        logger.info("Entering LONG position (%d shares) at market …", qty)
        order_id = place_initial_order(trd_ctx, code, ft.TrdSide.BUY, qty)
        if not order_id:
            return

        # Wait briefly, then check fill
        time.sleep(2)
        if is_position_closed(trd_ctx, order_id):
            logger.info("Entry order filled immediately — no trailing needed.")
            return

        # Trail state
        entry_price = price
        current_stop = entry_price * (1 - trail_pct)
        logger.info(
            "Trail initialised: entry=%.2f  stop=%.2f  trail_pct=%.1f%%",
            entry_price, current_stop, trail_pct * 100,
        )

        # ── Trail loop ────────────────────────────────────────────────
        while time.time() < deadline:
            last = get_last_price(quote_ctx, code)
            if last is None:
                time.sleep(1)
                continue

            # Move stop up if price has risen
            new_stop = last * (1 - trail_pct)
            if new_stop > current_stop + min_tick_move:
                logger.info(
                    "Price %.2f → new stop %.2f (was %.2f)",
                    last, new_stop, current_stop,
                )
                cancel_order(trd_ctx, order_id)
                order_id = place_stop_order(
                    trd_ctx, code, ft.TrdSide.SELL,
                    qty, new_stop,
                )
                current_stop = new_stop

            # Check if stop was hit
            if last <= current_stop:
                logger.warning("🔴 STOP HIT at %.2f  (entry %.2f)", last, entry_price)
                break

            time.sleep(3)  # poll every 3 s

        else:
            logger.info("⏰ Time limit reached — closing position.")

    finally:
        logger.info("Cleaning up — cancelling all open orders …")
        trd_ctx.cancel_all_order(cancel_all_orders=True, trd_env=TRD_ENV)
        quote_ctx.close()
        trd_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()