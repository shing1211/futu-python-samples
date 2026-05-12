# -*- coding: utf-8 -*-
"""复权数据 (get_rehab — 除权除息记录)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    print("=== get_rehab: HK.00700 ===")
    ret, data = ctx.get_rehab("HK.00700")
    if ret == 0:
        print(f"Total: {len(data)} records")
        print(data.to_string())
    else:
        print("error:", data)

    ctx.close()
