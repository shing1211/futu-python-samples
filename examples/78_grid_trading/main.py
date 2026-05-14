"""Grid Trading Bot — SIMULATE only.

Places buy and sell orders at evenly spaced price levels within a defined
range. When price drops to a lower grid level, it buys. When price rises
to a higher grid level, it sells. Profits from price oscillation.

Usage:
    python3 main.py [--stock HK.00700] [--grids 10] [--range-pct 0.10]
                    [--qty-per-grid 100] [--max-minutes 30]
"""

import sys
import os
import logging
import argparse
import time
from collections import OrderedDict

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
DEFAULT_GRIDS = 10
DEFAULT_RANGE_PCT = 0.10   # 10 % total range
DEFAULT_QTY_PER_GRID = 100
DEFAULT_MAX_MINUTES = 30
PRICE_TOLERANCE = 0.001    # for float comparison
TRD_ENV = ft.TrdEnv.SIMULATE


# ---------------------------------------------------------------------------
# Grid logic
# ---------------------------------------------------------------------------

def build_grid(center_price, grid_count, range_pct):
    """Build evenly spaced grid levels around center_price.

    Returns an OrderedDict: {price_level: {"side": "BUY"/"SELL", "order_id": None}}.
    """
    half_range = center_price * range_pct / 2
    step = half_range * 2 / grid_count

    levels = OrderedDict()
    for i in range(grid_count + 1):
        price = round(center_price - half_range + step * i, 4)
        levels[price] = {"side": None, "order_id": None, "filled": False}

    return levels


def assign_grid_orders(levels, center_price):
    """Mark each grid level as BUY (below center) or SELL (above center)."""
    for price, info in levels.items():
        if price < center_price - PRICE_TOLERANCE:
            info["side"] = "BUY"
        elif price > center_price + PRICE_TOLERANCE:
            info["side"] = "SELL"
        else:
            info["side"] = "NEUTRAL"  # center level, skip


def get_active_grid_orders(trd_ctx, grid_levels):
    """Check which grid orders are still open. Returns set of order_ids."""
    ret, orders = trd_ctx.order_list_query(trd_env=TRD_ENV)
    if ret != ft.RetCode.SUCCESS:
        return set()

    open_ids = set()
    for _, row in orders.iterrows():
        status = row.get("order_status", "")
        if status not in (ft.OrderStatus.FILLED_ALL, ft.OrderStatus.CANCELLED_ALL):
            open_ids.add(row["order_id"])
    return open_ids

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Grid Trading Bot (SIMULATE)")
    parser.add_argument("--stock", default=DEFAULT_STOCK, help="Stock ticker")
    parser.add_argument("--grids", type=int, default=DEFAULT_GRIDS,
                        help="Number of grid levels (default 10)")
    parser.add_argument("--range-pct", type=float, default=DEFAULT_RANGE_PCT,
                        help="Total price range as fraction (default 0.10)")
    parser.add_argument("--qty-per-grid", type=int, default=DEFAULT_QTY_PER_GRID,
                        help="Quantity per grid level (default 100)")
    parser.add_argument("--max-minutes", type=float, default=DEFAULT_MAX_MINUTES,
                        help="Maximum runtime in minutes (default 30)")
    args = parser.parse_args()

    code = args.stock
    grid_count = args.grids
    range_pct = args.range_pct
    qty = args.qty_per_grid
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

        # ── Get current price ──────────────────────────────────────────
        ret, df = quote_ctx.get_stock_quote(code)
        if ret != ft.RetCode.SUCCESS:
            logger.error("Cannot fetch quote for %s", code)
            return
        center_price = float(df.iloc[-1]["last_price"])
        logger.info("Current price for %s: %.2f", code, center_price)

        # ── Build grid ─────────────────────────────────────────────────
        levels = build_grid(center_price, grid_count, range_pct)
        assign_grid_orders(levels, center_price)

        low = min(levels.keys())
        high = max(levels.keys())
        step = list(levels.keys())[1] - list(levels.keys())[0]
        print(f"\n{'='*60}")
        print(f"  GRID TRADING BOT — {code}")
        print(f"  Center: {center_price:.2f}  Range: [{low:.2f}, {high:.2f}]")
        print(f"  Grids: {grid_count}  Step: {step:.4f}  Qty/level: {qty}")
        print(f"{'='*60}")

        # ── Place initial orders at all grid levels ────────────────────
        placed = 0
        for price, info in levels.items():
            if info["side"] == "BUY":
                order_id = _place_order(trd_ctx, code, ft.TrdSide.BUY,
                                         qty, price, "grid_buy")
                if order_id:
                    info["order_id"] = order_id
                    placed += 1
            elif info["side"] == "SELL":
                order_id = _place_order(trd_ctx, code, ft.TrdSide.SELL,
                                         qty, price, "grid_sell")
                if order_id:
                    info["order_id"] = order_id
                    placed += 1

        logger.info("Placed %d grid orders out of %d levels.", placed, len(levels))

        # ── Monitor and refill ─────────────────────────────────────────
        deadline = time.time() + max_seconds
        trades_log = []

        while time.time() < deadline:
            time.sleep(5)

            # Check which orders got filled
            open_ids = get_active_grid_orders(trd_ctx, levels)
            for price, info in levels.items():
                if info["order_id"] and info["order_id"] not in open_ids:
                    if not info["filled"]:
                        info["filled"] = True
                        trades_log.append({
                            "price": price,
                            "side": info["side"],
                            "time": time.strftime("%H:%M:%S"),
                        })
                        logger.info("✅ FILLED: %s %d shares at %.2f",
                                    info["side"], qty, price)

                        # Re-place order on opposite side (maintain grid)
                        if info["side"] == "BUY":
                            # Bought here → re-sell at this level
                            new_id = _place_order(trd_ctx, code, ft.TrdSide.SELL,
                                                  qty, price, "grid_refill_sell")
                            if new_id:
                                info["order_id"] = new_id
                                info["filled"] = False
                        elif info["side"] == "SELL":
                            # Sold here → re-buy at this level
                            new_id = _place_order(trd_ctx, code, ft.TrdSide.BUY,
                                                  qty, price, "grid_refill_buy")
                            if new_id:
                                info["order_id"] = new_id
                                info["filled"] = False

            # Status print
            filled_count = sum(1 for v in levels.values() if v["filled"])
            if filled_count > 0 and filled_count % 3 == 0 and filled_count > getattr(
                main, "_last_report", -1
            ):
                main._last_report = filled_count
                logger.info("📊 Grid status: %d/%d trades executed",
                            filled_count, len(levels))

        # ── Summary ────────────────────────────────────────────────────
        print(f"\n{'='*60}")
        print(f"  📊 GRID TRADING SUMMARY")
        print(f"{'='*60}")
        total_buys = sum(1 for t in trades_log if t["side"] == "BUY")
        total_sells = sum(1 for t in trades_log if t["side"] == "SELL")
        for t in trades_log[-10:]:
            print(f"  {t['time']}  {t['side']:<5} @ {t['price']:.2f}")
        print(f"  Total: {total_buys} buys, {total_sells} sells")
        print(f"{'='*60}")

    finally:
        logger.info("Cleaning up — cancelling all open orders …")
        trd_ctx.cancel_all_order(cancel_all_orders=True, trd_env=TRD_ENV)
        quote_ctx.close()
        trd_ctx.close()
        logger.info("Done.")


def _place_order(trd_ctx, code, side, qty, price, remark):
    """Place a limit order. Returns order_id or None."""
    ret, order_id = trd_ctx.place_order(
        price=price,
        code=code,
        qty=qty,
        trd_side=side,
        order_type=ft.OrderType.NORMAL,
        trd_env=TRD_ENV,
        remark=remark,
    )
    if ret != ft.RetCode.SUCCESS:
        logger.error("place_order(%s, %.2f) failed: %s", side, price, ret)
        return None
    return order_id


if __name__ == "__main__":
    main()