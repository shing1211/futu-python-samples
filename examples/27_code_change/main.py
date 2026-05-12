# -*- coding: utf-8 -*-
"""股票代码变更查询 (get_code_change)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    codes = ["HK.00700", "HK.00005"]

    print("=== get_code_change ===")
    ret, data = ctx.get_code_change(code_list=codes)
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    ctx.close()
