# -*- coding: utf-8 -*-
"""期权链 (get_option_chain / get_option_expiration_date)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    # 指数期权 — 先查到期日
    code = "US.NDX"

    print(f"=== get_option_expiration_date: {code} ===")
    ret, dates = ctx.get_option_expiration_date(code, ft.IndexOptionType.NORMAL)
    if ret == 0:
        print(dates[:5] if isinstance(dates, list) else dates)
    else:
        print("error:", dates)

    # 取最近一个到期日，查期权链
    if ret == 0 and isinstance(dates, list) and len(dates) > 0:
        nearest = dates[0]
        print(f"\n=== get_option_chain: {code} @ {nearest} ===")
        ret, data = ctx.get_option_chain(
            code,
            index_option_type=ft.IndexOptionType.NORMAL,
            start=nearest,
            end=nearest,
            option_type=ft.OptionType.ALL,
        )
        if ret == 0:
            print(f"Total contracts: {len(data)}")
            print(data.head(5).to_string())
        else:
            print("error:", data)

    ctx.close()
