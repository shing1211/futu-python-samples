"""Stop-Loss / Take-Profit Engine — SIMULATE only.

Dual SL/TP framework with configurable risk-reward, partial exits, and
trailing activation. Complements the trailing stop (68) with a complete
entry → TP/SL lifecycle.

Usage:
    python3 main.py [--stock HK.00700] [--risk-reward 2.0]
                    [--partial-exit 0.5] [--max-minutes 15]
"""

import sys
import logging
import argparse
import time

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
DEFAULT_RISK_REWARD = 2.0       # TP distance = RR × SL distance
DEFAULT_PARTIAL_EXIT = 0.5      # close 50 % at TP1, rest trails
DEFAULT_MAX_MINUTES = 15
PRICE_TOLERANCE = 0.001
TRD_ENV = ft.TrdEnv.SIMULATE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_last_price(quote_ctx, code):
    ret, df = quote_ctx.get_stock_quote(code)
    if ret != ft.RetCode.SUCCESS:
        return None
    return float(df.iloc[-1]["last_price"])


def place_order(trd_ctx, code, side, qty, price, order_type, remark):
    ret, order_id = trd_ctx.place_order(
        price=price,
        code=code,
        qty=qty,
        trd_side=side,
        order_type=order_type,
        trd_env=TRD_ENV,
        remark=remark,
    )
    if ret != ft.RetCode.SUCCESS:
        logger.error("place_order(%s, %s, %s) failed: %s", side, code, remark, ret)
        return None
    return order_id


def cancel_order(trd_ctx, order_id):
    if not order_id:
        return True
    ret, _ = trd_ctx.cancel_order(order_id, trd_env=TRD_ENV)
    if ret != ft.RetCode.SUCCESS:
        logger.warning("cancel_order(%s) failed: %s", order_id, ret)
        return False
    logger.info("Order %s cancelled", order_id)
    return True


def get_order_status(trd_ctx, order_id):
    """Returns (status_str, filled_qty) or (None, 0)."""
    ret, orders = trd_ctx.order_list_query(trd_env=TRD_ENV)
    if ret != ft.RetCode.SUCCESS:
        return None, 0
    for _, row in orders.iterrows():
        if row["order_id"] == order_id:
            return row.get("order_status", ""), float(row.get("fill_qty", 0) or 0)
    return "NOT_FOUND", 0


def is_order_done(trd_ctx, order_id):
    """True if order is fully filled or fully cancelled."""
    if not order_id:
        return True
    status, filled = get_order_status(trd_ctx, order_id)
    return status in (
        ft.OrderStatus.FILLED_ALL,
        ft.OrderStatus.CANCELLED_ALL,
        ft.OrderStatus.DISABLED,
    )


def get_position_qty(trd_ctx, code):
    """Get current position quantity for code."""
    ret, df = trd_ctx.position_list_query(trd_env=TRD_ENV)
    if ret != ft.RetCode.SUCCESS or df is None or df.empty:
        return 0
    for _, row in df.iterrows():
        if row.get("code", "") == code:
            return int(float(row.get("qty", 0) or 0))
    return 0

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="SL/TP Engine (SIMULATE)")
    parser.add_argument("--stock", default=DEFAULT_STOCK, help="Stock ticker")
    parser.add_argument("--risk-reward", type=float, default=DEFAULT_RISK_REWARD,
                        help="Risk-reward ratio (default 2.0)")
    parser.add_argument("--partial-exit", type=float, default=DEFAULT_PARTIAL_EXIT,
                        help="Fraction to close at TP1 (default 0.5)")
    parser.add_argument("--max-minutes", type=float, default=DEFAULT_MAX_MINUTES,
                        help="Safety timeout (default 15)")
    args = parser.parse_args()

    code = args.stock
    rr = args.risk_reward
    partial_exit = args.partial_exit
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

        # ── Entry price ────────────────────────────────────────────────
        entry = get_last_price(quote_ctx, code)
        if entry is None:
            logger.error("Cannot fetch price for %s", code)
            return
        logger.info("Entry price for %s: %.2f", code, entry)

        # ── Compute SL/TP levels ───────────────────────────────────────
        atr_pct = 0.02  # 2 % ATR proxy for stop distance
        sl_distance = entry * atr_pct
        tp1_distance = sl_distance * rr

        sl_price = round(entry - sl_distance, 4)   # stop-loss below entry
        tp1_price = round(entry + tp1_distance, 4)  # take-profit 1
        tp1_qty = int(100 * partial_exit)            # partial exit qty
        tp2_qty = 100 - tp1_qty                       # remainder trails

        print(f"\n{'='*60}")
        print(f"  🎯 SL/TP ENGINE — {code}")
        print(f"{'='*60}")
        print(f"  Entry:        {entry:.2f}")
        print(f"  Stop-Loss:    {sl_price:.2f}  (-{atr_pct*100:.1f}%)")
        print(f"  TP1:          {tp1_price:.2f}  (+{tp1_distance/entry*100:.1f}%)  qty={tp1_qty}")
        print(f"  TP2 (trail):  remaining {tp2_qty} shares")
        print(f"  Risk-Reward:  1 : {rr}")
        print(f"{'='*60}")

        # ── Place entry order ──────────────────────────────────────────
        entry_id = place_order(trd_ctx, code, ft.TrdSide.BUY, 100, 0,
                               ft.OrderType.NORMAL, "sl_tp_entry")
        if not entry_id:
            return
        print(f"\n  📥 Entry order placed: {entry_id}")

        # Wait for fill
        print("  Waiting for entry fill …")
        for _ in range(60):  # up to 3 min
            time.sleep(3)
            status, filled = get_order_status(trd_ctx, entry_id)
            if status in (ft.OrderStatus.FILLED_ALL, ft.OrderStatus.FILLED_PART):
                actual_qty = int(filled)
                print(f"  ✅ Entry filled: {actual_qty} shares")
                break
            if status == ft.OrderStatus.CANCELLED_ALL:
                print("  ❌ Entry cancelled — exiting.")
                return
        else:
            print("  ⏰ Entry not filled in time — cancelling.")
            return

        # Adjust qty for partial fills
        tp1_qty = int(actual_qty * partial_exit)
        tp2_qty = actual_qty - tp1_qty

        # ── Place TP1 limit order ──────────────────────────────────────
        tp1_id = place_order(trd_ctx, code, ft.TrdSide.SELL, tp1_qty,
                             tp1_price, ft.OrderType.NORMAL, "sl_tp_tp1")

        # ── Place SL stop order ────────────────────────────────────────
        sl_id = place_order(trd_ctx, code, ft.TrdSide.SELL, tp2_qty,
                            sl_price, ft.OrderType.STOP, "sl_tp_stop")

        # ── Monitor loop ───────────────────────────────────────────────
        deadline = time.time() + max_seconds
        tp1_filled = False
        sl_triggered = False

        while time.time() < deadline:
            time.sleep(3)

            # Check TP1
            if tp1_id and not tp1_filled:
                status, filled = get_order_status(trd_ctx, tp1_id)
                if status in (ft.OrderStatus.FILLED_ALL, ft.OrderStatus.FILLED_PART):
                    print(f"\n  🎉 TP1 HIT! {int(filled)} shares at limit {tp1_price:.2f}")
                    tp1_filled = True
                    # Cancel SL, trail remaining
                    if sl_id:
                        cancel_order(trd_ctx, sl_id)
                        sl_id = None
                        # Re-place remaining as trailing stop
                        new_sl = round(entry + tp1_distance * 0.5, 4)  # breakeven-ish
                        sl_id = place_order(trd_ctx, code, ft.TrdSide.SELL, tp2_qty,
                                            new_sl, ft.OrderType.STOP, "sl_tp_trail")
                        print(f"  🔄 SL moved to breakeven zone: {new_sl:.2f}")

            # Check SL
            if sl_id and not sl_triggered:
                status, filled = get_order_status(trd_ctx, sl_id)
                if status in (ft.OrderStatus.FILLED_ALL, ft.OrderStatus.FILLED_PART):
                    print(f"\n  🛑 STOP-LOSS HIT! {int(filled)} shares at {sl_price:.2f}")
                    sl_triggered = True
                    if tp1_id:
                        cancel_order(trd_ctx, tp1_id)
                    break

            # If both legs done
            if tp1_filled and sl_triggered:
                break

        # Summary
        print(f"\n{'='*60}")
        print(f"  📊 TRADE SUMMARY")
        print(f"{'='*60}")
        print(f"  Entry:       {entry:.2f} × {actual_qty}")
        if tp1_filled:
            print(f"  TP1 exit:    {tp1_price:.2f} × {tp1_qty}")
        if sl_triggered:
            print(f"  SL exit:     {sl_price:.2f} × {tp2_qty}")
        print(f"{'='*60}")

    finally:
        logger.info("Cleaning up — cancelling all open orders …")
        trd_ctx.cancel_all_order(cancel_all_orders=True, trd_env=TRD_ENV)
        quote_ctx.close()
        trd_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()