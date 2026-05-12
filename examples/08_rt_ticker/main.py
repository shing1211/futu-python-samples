# -*- coding: utf-8 -*-
"""获取分时成交明细 (get_rt_ticker)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    code = "HK.00700"

    # 获取今日分时成交 (逐笔)
    print("=== get_rt_ticker ===")
    ret, data = ctx.get_rt_ticker(code, num=50)
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    # 获取分时数据
    print("\n=== get_rt_data ===")
    ret, data = ctx.get_rt_data(code)
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    ctx.close()
