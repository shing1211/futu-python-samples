# -*- coding: utf-8 -*-
"""期货合约信息 (get_future_info)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    codes = ["HK.HSImain", "US.NDQmain"]
    print("=== get_future_info ===")
    ret, data = ctx.get_future_info(codes)
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    ctx.close()
