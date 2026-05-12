# -*- coding: utf-8 -*-
"""K线配额查询 (get_history_kl_quota)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    print("=== get_history_kl_quota ===")
    ret, data = ctx.get_history_kl_quota()
    if ret == 0:
        print(f"used: {data['used_quota']}  remain: {data['remain_quota']}")
    else:
        print("error:", data)

    print("\n=== get_history_kl_quota (detail=True) ===")
    ret, data = ctx.get_history_kl_quota(get_detail=True)
    if ret == 0:
        print(f"used: {data['used_quota']}  remain: {data['remain_quota']}  detail: {data.get('detail', 'N/A')}")
    else:
        print("error:", data)

    ctx.close()
