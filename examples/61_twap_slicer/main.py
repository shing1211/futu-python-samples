#!/usr/bin/env python3
"""
61 — TWAP Order Slicer

Slice a large simulated order into N child orders over M minutes.
Each slice reads the order book to price at the best bid (sell) or
best ask (buy) without sweeping the spread.

SIMULATE account only — no real orders.

SDK: OpenSecTradeContext.place_order()
               .order_list_query()
               .cancel_all_order()
               .unlock_trade()
    OpenQuoteContext.get_order_book()
               .get_market_snapshot()
"""

import sys
import time
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context, create_trade_context, get_demo_trade_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s): %(message)s")
logger = logging.getLogger(__name__)

STOCK = "HK.00700"
SIDE = ft.TrdSide.SELL
TOTAL_QTY = 1000
NUM_SLICES = 10
INTERVAL_SEC = 30
TRD_ENV = ft.TrdEnv.SIMULATE
MAX_PRICE_MOVE_PCT = 5.0


def get_lot_size(ctx):
    ret, snap = ctx.get_market_snapshot([STOCK])
    if ret == ft.RET_OK and snap is not None and not snap.empty:
        return int(snap.iloc[0].get("lot_size", 100))
    return 100


def get_book_price(ctx):
    ret, book = ctx.get_order_book(STOCK, num=1)
    if ret != 0:
        return None
    if SIDE == ft.TrdSide.SELL:
        bid = book.get("Bid", [])
        return float(bid[0][0]) if bid else None
    else:
        ask = book.get("Ask", [])
        return float(ask[0][0]) if ask else None


def main():
    print(f"  === TWAP Order Slicer ===\n")
    print(f"  IMPORTANT: SIMULATE account only. No real orders.\n")
    print(f"  Stock: {STOCK}")
    print(f"  Side: {SIDE}")
    print(f"  Total qty: {TOTAL_QTY}")
    print(f"  Slices: {NUM_SLICES} x {TOTAL_QTY // NUM_SLICES} @ {INTERVAL_SEC}s intervals\n")

    quote_ctx = create_quote_context()
    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)

    try:
        ret, data = trd_ctx.unlock_trade(get_demo_trade_password())
        if ret != ft.RET_OK:
            print(f"  unlock_trade failed: {data}")
            return

        lot_size = get_lot_size(quote_ctx)
        slice_qty = (TOTAL_QTY // NUM_SLICES // lot_size) * lot_size
        if slice_qty < lot_size:
            slice_qty = lot_size
        actual_total = slice_qty * NUM_SLICES

        ret2, snap = quote_ctx.get_market_snapshot([STOCK])
        arrival_price = 0.0
        if ret2 == ft.RET_OK and snap is not None and not snap.empty:
            arrival_price = float(snap.iloc[0].get("last_price", 0))
        print(f"  Lot size: {lot_size}  Slice qty: {slice_qty}  Total: {actual_total}")
        print(f"  Arrival price: {arrival_price:.2f}\n")
        print(f"  {'='*60}")

        fills = []
        for i in range(NUM_SLICES):
            print(f"\n  Slice {i+1}/{NUM_SLICES} — waiting {INTERVAL_SEC}s...")
            time.sleep(INTERVAL_SEC)

            price = get_book_price(quote_ctx)
            if price is None:
                print(f"  No bid/ask available — skipping slice")
                continue

            if arrival_price and abs(price - arrival_price) / arrival_price * 100 > MAX_PRICE_MOVE_PCT:
                print(f"  Price moved {abs(price-arrival_price)/arrival_price*100:.1f}% "
                      f"(>{MAX_PRICE_MOVE_PCT}%) — pausing slice")
                continue

            ret3, result = trd_ctx.place_order(
                price=price, qty=slice_qty, code=STOCK,
                trd_side=SIDE, order_type=ft.OrderType.NORMAL,
                trd_env=TRD_ENV,
            )
            order_id = result.get("order_id", "N/A") if ret3 == ft.RET_OK else "N/A"
            print(f"  {'PLACED' if ret3 == ft.RET_OK else 'FAILED'}: "
                  f"price={price:.2f} qty={slice_qty} order_id={order_id}")

            if ret3 == ft.RET_OK:
                fills.append({"price": price, "qty": slice_qty, "order_id": order_id})

            time.sleep(2)

            ret4, orders = trd_ctx.order_list_query(
                status_filter_list=[ft.OrderStatus.SUBMITTED,
                                    ft.OrderStatus.FILLED_PART,
                                    ft.OrderStatus.FILLED_ALL],
                trd_env=TRD_ENV,
            )
            if ret4 == ft.RET_OK and orders is not None and not orders.empty:
                filled_orders = orders[orders["code"] == STOCK]
                if not filled_orders.empty:
                    cum_qty = int(filled_orders.iloc[0].get("dealt_qty",
                                  filled_orders.iloc[0].get("fill_qty", 0)))
                    print(f"  Cumulative filled: {cum_qty}")

        print(f"\n  {'='*60}")
        print(f"  TWAP SUMMARY")
        print(f"  {'='*60}")

        if fills:
            total_filled = sum(f["qty"] for f in fills)
            twap = sum(f["price"] * f["qty"] for f in fills) / total_filled if total_filled else 0
            slippage_bps = ((twap - arrival_price) / arrival_price * 10000) if arrival_price else 0
            print(f"  Slices placed: {len(fills)}/{NUM_SLICES}")
            print(f"  Total filled:  {total_filled}")
            print(f"  TWAP:          {twap:.2f}")
            print(f"  Arrival:       {arrival_price:.2f}")
            print(f"  Slippage:      {slippage_bps:+.1f} bps")
        else:
            print(f"  No orders placed")

    finally:
        print(f"\n  Cleaning up remaining orders...")
        ret5, _ = trd_ctx.cancel_all_order(trd_env=TRD_ENV)
        print(f"  cancel_all_order: ret={ret5}")
        quote_ctx.close()
        trd_ctx.close()
        print(f"  Done.")


if __name__ == "__main__":
    main()
