# -*- coding: utf-8 -*-
"""资金流向 (get_capital_flow / get_capital_distribution)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    code = "HK.00700"

    # 资金流向 (分时)
    print("=== get_capital_flow: intraday ===")
    ret, data = ctx.get_capital_flow(code, period_type=ft.PeriodType.INTRADAY)
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    # 资金流向 (日K)
    print("\n=== get_capital_flow: day ===")
    ret, data = ctx.get_capital_flow(code, period_type=ft.PeriodType.DAY)
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    # 资金分布 (大单/中单/小单)
    print("\n=== get_capital_distribution ===")
    ret, data = ctx.get_capital_distribution(code)
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    ctx.close()
