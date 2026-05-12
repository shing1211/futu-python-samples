# -*- coding: utf-8 -*-
"""获取交易日历 (get_trading_days)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    for market in [ft.Market.HK, ft.Market.US, ft.Market.SH, ft.Market.SZ]:
        print(f"\n=== request_trading_days: {market} ===")
        ret, data = ctx.request_trading_days(market, "2026-04-01", "2026-05-31")
        if ret == 0:
            print(data.to_string())
        else:
            print("error:", data)

    ctx.close()
