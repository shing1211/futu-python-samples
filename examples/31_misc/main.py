# -*- coding: utf-8 -*-
"""持仓变动 / 复权数据 / K线限制配额 / 用户分组 (杂项)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    code = "HK.00700"

    # 持仓变动
    print(f"=== get_holding_change_list: {code} ===")
    ret, data = ctx.get_holding_change_list(
        code,
        holder_type=ft.StockHolder.EXECUTIVE,
        start="2025-01-01",
        end="2026-05-12",
    )
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    # 复权数据
    print(f"\n=== get_rehab: {code} ===")
    ret, data = ctx.get_rehab(code)
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    # 自选股分组列表
    print("\n=== get_user_security_group ===")
    ret, data = ctx.get_user_security_group()
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    ctx.close()
