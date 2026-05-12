# -*- coding: utf-8 -*-
"""账户最大可买可卖数量 (acctradinginfo_query)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_trade_context


if __name__ == "__main__":
    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)

    # 先解锁
    ret, data = trd_ctx.unlock_trade("123456")
    print("unlock:", ret, "OK" if ret == 0 else data)

    code = "HK.00700"
    price = 400.0

    # 查询最大买入
    print(f"\n=== acctradinginfo_query: {code} @ {price} (BUY) ===")
    ret, data = trd_ctx.acctradinginfo_query(
        order_type=ft.OrderType.NORMAL,
        code=code,
        price=price,
        trd_env=ft.TrdEnv.REAL,
    )
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    # 查询最大卖出
    print(f"\n=== acctradinginfo_query: {code} @ {price} (SELL) ===")
    ret, data = trd_ctx.acctradinginfo_query(
        order_type=ft.OrderType.NORMAL,
        code=code,
        price=price,
        trd_side=ft.TrdSide.SELL,
        trd_env=ft.TrdEnv.REAL,
    )
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    trd_ctx.close()
