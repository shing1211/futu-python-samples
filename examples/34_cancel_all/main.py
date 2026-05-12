# -*- coding: utf-8 -*-
"""取消所有订单 (cancel_all_order)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_trade_context


if __name__ == "__main__":
    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)

    ret, data = trd_ctx.unlock_trade("123456")
    print("unlock:", ret, "OK" if ret == 0 else data)

    # 先看一下当前提交的订单
    print("\n=== order_list_query: SUBMITTED ===")
    ret, data = trd_ctx.order_list_query(
        status_filter_list=[ft.OrderStatus.SUBMITTED],
    )
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    # 取消所有订单
    print("\n=== cancel_all_order ===")
    ret, data = trd_ctx.cancel_all_order(trd_env=ft.TrdEnv.REAL)
    print("cancel_all:", ret, data)

    trd_ctx.close()
