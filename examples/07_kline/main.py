# -*- coding: utf-8 -*-
"""获取K线数据 (get_cur_kline / request_history_kline)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    code = "HK.00700"

    # 实时K线 (当前K线状态)
    print("=== get_cur_kline (实时) ===")
    ret, data = ctx.get_cur_kline(code, num=10, ktype=ft.KLType.K_DAY, AuType=ft.AuType.qfq)
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    # 历史K线
    print("\n=== request_history_kline (近30天) ===")
    ret, data = ctx.request_history_kline(
        code,
        start="2026-04-01",
        end="2026-05-12",
        ktype=ft.KLType.K_DAY,
        AuType=ft.AuType.qfq,
    )
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    ctx.close()
