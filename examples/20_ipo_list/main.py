# -*- coding: utf-8 -*-
"""IPO列表 (get_ipo_list)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    for market in [ft.Market.HK, ft.Market.US]:
        print(f"\n=== get_ipo_list: {market} ===")
        ret, data = ctx.get_ipo_list(market)
        if ret == 0:
            print(f"Total: {len(data)}")
            print(data.head(5).to_string())
        else:
            print("error:", data)

    ctx.close()
