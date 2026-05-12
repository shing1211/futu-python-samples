# -*- coding: utf-8 -*-
"""查询已订阅列表 (get_sub_list)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    # 先订阅几个品种
    codes = ["HK.00700", "HK.HSImain", "US.AAPL"]
    subtypes = [ft.SubType.QUOTE, ft.SubType.K_DAY, ft.SubType.ORDER_BOOK]
    ret = ctx.subscribe(codes, subtypes)
    print("subscribe ret:", ret)

    # 查询已订阅
    print("\n=== query_subscription ===")
    ret, data = ctx.query_subscription()
    if ret == 0:
        print(data)
    else:
        print("error:", data)

    ctx.close()
