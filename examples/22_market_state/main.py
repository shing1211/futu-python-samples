# -*- coding: utf-8 -*-
"""市场状态 (get_market_state) — 盘前/盘中/盘后/ Closed"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    codes = ["HK.00700", "US.AAPL", "SH.600000", "SZ.000001"]
    print("=== get_market_state ===")
    ret, data = ctx.get_market_state(codes)
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    ctx.close()
