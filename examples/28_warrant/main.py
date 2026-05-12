# -*- coding: utf-8 -*-
"""涡轮/窝轮数据 (get_warrant)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    # 查腾讯的涡轮
    owner = "HK.00700"
    print(f"=== get_warrant: owner={owner} ===")
    ret, data = ctx.get_warrant(stock_owner=owner)
    if ret == 0:
        print(f"Total warrants: {len(data)}")
        print(data.head(5).to_string())
    else:
        print("error:", data)

    ctx.close()
