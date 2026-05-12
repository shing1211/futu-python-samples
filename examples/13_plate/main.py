# -*- coding: utf-8 -*-
"""获取板块列表 (get_plate_list / get_plate_stock)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    # 枚举板块列表
    print("=== get_plate_list: HK ===")
    ret, data = ctx.get_plate_list(ft.Market.HK, ft.Plate.ALL)
    if ret == 0:
        print(f"Total plates: {len(data)}")
        print(data.head(10).to_string())
    else:
        print("error:", data)

    # 取一个板块，看里面有哪些股票
    if ret == 0 and len(data) > 0:
        first_plate = data.iloc[0]['code']
        print(f"\n=== get_plate_stock: {first_plate} ===")
        ret2, stock_list = ctx.get_plate_stock(first_plate)
        if ret2 == 0:
            print(stock_list.head(10).to_string())
        else:
            print("error:", stock_list)

    ctx.close()
