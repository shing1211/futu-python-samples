# -*- coding: utf-8 -*-
"""股票基本信息 (get_stock_basicinfo)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    # 按市场查
    print("=== get_stock_basicinfo: HK STOCK (first 5) ===")
    ret, data = ctx.get_stock_basicinfo(
        market=ft.Market.HK,
        stock_type=ft.SecurityType.STOCK,
    )
    if ret == 0:
        print(f"Total: {len(data)}")
        print(data.head(5).to_string())
    else:
        print("error:", data)

    # 按代码列表查
    print("\n=== get_stock_basicinfo: specific codes ===")
    ret, data = ctx.get_stock_basicinfo(
        market=ft.Market.HK,
        code_list=["HK.00700", "HK.00005", "HK.HSImain"],
    )
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    ctx.close()
