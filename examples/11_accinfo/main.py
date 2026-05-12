# -*- coding: utf-8 -*-
"""账户资金查询 (accinfo_query / position_list_query)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context, create_trade_context


if __name__ == "__main__":
    quote_ctx = create_quote_context()
    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)

    # 解锁交易 (模拟密码)
    ret, data = trd_ctx.unlock_trade("123456")
    print("unlock_trade:", ret, data if ret != 0 else "OK")

    # 账户资金
    print("\n=== accinfo_query ===")
    ret, data = trd_ctx.accinfo_query()
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    # 持仓列表
    print("\n=== position_list_query ===")
    ret, data = trd_ctx.position_list_query()
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    quote_ctx.close()
    trd_ctx.close()
