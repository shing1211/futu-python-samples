# -*- coding: utf-8 -*-
"""获取相关股票列表 / 所属板块 (get_owner_plate / get_referencestock_list)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    code = "HK.00700"

    # 所属板块
    print(f"=== get_owner_plate: {code} ===")
    ret, data = ctx.get_owner_plate([code])
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    # 相关股票 (窝轮/牛熊证相关)
    print(f"\n=== get_referencestock_list: {code} ===")
    for ref_type in [ft.SecurityReferenceType.WARRANT, ft.SecurityReferenceType.BULL_BEAR]:
        ret, data = ctx.get_referencestock_list(code, ref_type)
        if ret == 0:
            print(f"  [{ref_type}]: {len(data)} records")
            print(data.head(5).to_string())
        else:
            print(f"  [{ref_type}] error:", data)

    ctx.close()
