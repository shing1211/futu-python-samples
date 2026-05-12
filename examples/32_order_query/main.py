# -*- coding: utf-8 -*-
"""订单查询 / 改单 / 撤单 / 成交查询 (order_list_query / modify_order / deal_list_query)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_trade_context


if __name__ == "__main__":
    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)

    # 解锁 (模拟密码)
    ret, data = trd_ctx.unlock_trade("123456")
    print("unlock:", ret, "OK" if ret == 0 else data)

    # 当前订单列表
    print("\n=== order_list_query: SUBMITTED ===")
    ret, data = trd_ctx.order_list_query(
        status_filter_list=[ft.OrderStatus.SUBMITTED],
    )
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    # 历史订单
    print("\n=== history_order_list_query ===")
    ret, data = trd_ctx.history_order_list_query(
        status_filter_list=[ft.OrderStatus.FILLED_ALL],
        start="2026-01-01",
        end="2026-05-12",
    )
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    # 成交记录
    print("\n=== deal_list_query ===")
    ret, data = trd_ctx.deal_list_query()
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    # 历史成交
    print("\n=== history_deal_list_query ===")
    ret, data = trd_ctx.history_deal_list_query(
        start="2026-01-01",
        end="2026-05-12",
    )
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    trd_ctx.close()
