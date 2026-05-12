# -*- coding: utf-8 -*-
"""订单费用查询 (order_fee_query)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_trade_context


if __name__ == "__main__":
    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)

    ret, data = trd_ctx.unlock_trade("123456")
    print("unlock:", ret, "OK" if ret == 0 else data)

    # 先找一笔历史订单
    print("\n=== history_order_list_query (FILLED_ALL) ===")
    ret, orders = trd_ctx.history_order_list_query(
        status_filter_list=[ft.OrderStatus.FILLED_ALL],
        start="2026-01-01",
        end="2026-05-12",
    )
    if ret == 0 and len(orders) > 0:
        order_id = orders.iloc[0]["order_id"]
        print(f"Using order_id: {order_id}")

        # 查订单费用
        print(f"\n=== order_fee_query: {order_id} ===")
        ret, data = trd_ctx.order_fee_query(order_id_list=[order_id])
        if ret == 0:
            print(data.to_string())
        else:
            print("error:", data)
    else:
        print("no filled orders found, skipping fee query")

    trd_ctx.close()
