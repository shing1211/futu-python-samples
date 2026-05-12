# -*- coding: utf-8 -*-
"""查询账户持仓的保证金率 (get_margin_ratio)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_trade_context


if __name__ == "__main__":
    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)

    ret, data = trd_ctx.unlock_trade("123456")
    print("unlock:", ret, "OK" if ret == 0 else data)

    # 查持仓的保证金率
    print("\n=== get_margin_ratio: all positions ===")
    ret, data = trd_ctx.get_margin_ratio(code_list=[])
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    trd_ctx.close()
