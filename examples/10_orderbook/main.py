# -*- coding: utf-8 -*-
"""获取买卖盘 (get_order_book)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    code = "HK.00700"

    # 订阅摆盘
    ret = ctx.subscribe(code, ft.SubType.ORDER_BOOK)
    print("subscribe ret:", ret)

    # 获取10档买卖盘
    print("\n=== get_order_book (10档) ===")
    ret, data = ctx.get_order_book(code, num=10)
    if ret == 0:
        print("BID (买盘):")
        for i, (price, vol, count) in enumerate(data['Bid']):
            print(f"  {i+1:2d}. {price:>10.2f}  x {vol:>10.0f}  (共{count}笔)")
        print("ASK (卖盘):")
        for i, (price, vol, count) in enumerate(data['Ask']):
            print(f"  {i+1:2d}. {price:>10.2f}  x {vol:>10.0f}  (共{count}笔)")
    else:
        print("error:", data)

    ctx.close()
