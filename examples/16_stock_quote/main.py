# -*- coding: utf-8 -*-
"""获取报价 (get_stock_quote)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    codes = ["HK.00700", "HK.HSImain", "US.AAPL"]

    # 先订阅
    ctx.subscribe(codes, [ft.SubType.QUOTE])

    # 获取实时报价
    print("=== get_stock_quote ===")
    ret, data = ctx.get_stock_quote(codes)
    if ret == 0:
        # 打印关键字段
        cols = ["code", "name", "last_price", "open_price", "high_price",
                "low_price", "volume", "turnover", "pe_ratio"]
        available = [c for c in cols if c in data.columns]
        print(data[available].to_string())
    else:
        print("error:", data)

    ctx.close()
