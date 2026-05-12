# -*- coding: utf-8 -*-
"""资金流水 (get_acc_cash_flow)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_trade_context


if __name__ == "__main__":
    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)

    ret, data = trd_ctx.unlock_trade("123456")
    print("unlock:", ret, "OK" if ret == 0 else data)

    # 资金流水
    print("\n=== get_acc_cash_flow: REAL account ===")
    ret, data = trd_ctx.get_acc_cash_flow(
        clearing_date="",
        trd_env=ft.TrdEnv.REAL,
        cashflow_direction=ft.CashFlowDirection.ALL,
        start="2026-01-01",
        end="2026-05-12",
    )
    if ret == 0:
        print(f"Total: {len(data)} records")
        print(data.to_string())
    else:
        print("error:", data)

    trd_ctx.close()
