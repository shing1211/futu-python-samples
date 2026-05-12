# -*- coding: utf-8 -*-
"""相关股票列表 (get_referencestock_list)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    code = "HK.00700"

    for ref_type in [
        ft.SecurityReferenceType.WARRANT,
        ft.SecurityReferenceType.BULL_BEAR,
    ]:
        print(f"=== get_referencestock_list: {code} [{ref_type}] ===")
        ret, data = ctx.get_referencestock_list(code, ref_type)
        if ret == 0:
            print(f"Count: {len(data)}")
            print(data.head(5).to_string())
        else:
            print("error:", data)
        print()

    ctx.close()
