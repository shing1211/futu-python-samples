# -*- coding: utf-8 -*-
"""交易账户信息 (get_acc_list / get_user_info / get_security_firm)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_trade_context


if __name__ == "__main__":
    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)

    # 获取账户列表
    print("=== get_acc_list ===")
    ret, data = trd_ctx.get_acc_list()
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    # 获取券商信息
    print("\n=== get_security_firm ===")
    ret, data = trd_ctx.get_security_firm()
    if ret == 0:
        print(data)
    else:
        print("error:", data)

    # 获取用户信息
    print("\n=== get_user_info ===")
    ret, data = trd_ctx.get_user_info()
    if ret == 0:
        print(data)
    else:
        print("error:", data)

    trd_ctx.close()
