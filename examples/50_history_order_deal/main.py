#!/usr/bin/env python3
"""
50 — Historical Order and Deal History

Shows the full pipeline of closed orders and their fills --
everything that's already settled, not just live open orders.

  - history_order_list_query: closed/filled/cancelled orders
  - history_deal_list_query: actual fills with time, price, quantity

Use this to audit your trading history, calculate win rates,
average entry prices, and realised P&L per stock.

Note: defaults to trd_env='REAL'. For SIMULATE account results,
pass trd_env='SIMULATE' (or 'SIMU2' depending on your account type).

SDK: OpenSecTradeContext.history_order_list_query / history_deal_list_query
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import futu as ft
from connect import create_trade_context, get_demo_trade_password


def main():
    trd_ctx = create_trade_context()
    ret = trd_ctx.unlock_trade(get_demo_trade_password())
    if ret != 0:
        print(f"unlock_trade failed: {ret}")
        trd_ctx.close()
        return

    # Try SIMULATE first (demo account), then REAL if nothing came back
    for env in ["SIMULATE", "REAL"]:
        print(f"=== HISTORICAL ORDERS (env={env}) ===\n")
        ret, orders = trd_ctx.history_order_list_query(
            start="",       # empty = earliest available
            end="",
            trd_env=env,
        )
        if ret != 0:
            print(f"  history_order_list_query failed: {orders}\n")
        elif orders is None or (hasattr(orders, "empty") and orders.empty):
            print("  (no historical orders)\n")
        else:
            print(f"  Columns: {list(orders.columns)}")
            show_cols = ["code", "order_id", "order_type", "side", "price",
                         "qty", "status", "create_time"]
            available = [c for c in show_cols if c in orders.columns]
            print(orders[available].head(20).to_string(index=False))
            print(f"\n  Total: {len(orders)} orders\n")

        print(f"=== HISTORICAL DEALS (env={env}) ===\n")
        ret, deals = trd_ctx.history_deal_list_query(
            start="",
            end="",
            trd_env=env,
        )
        if ret != 0:
            print(f"  history_deal_list_query failed: {deals}\n")
        elif deals is None or (hasattr(deals, "empty") and deals.empty):
            print("  (no historical deals)\n")
        else:
            print(f"  Columns: {list(deals.columns)}")
            show_cols = ["code", "deal_id", "order_id", "side", "price", "qty", "create_time"]
            available = [c for c in show_cols if c in deals.columns]
            print(deals[available].head(20).to_string(index=False))
            print(f"\n  Total: {len(deals)} deals\n")

    trd_ctx.close()
    print("Done.")


if __name__ == "__main__":
    main()
