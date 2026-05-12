# -*- coding: utf-8 -*-
"""自选股分组管理 (get_user_security / modify_user_security)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    group = "MyTechStocks"

    # 查看分组里的股票
    print(f"=== get_user_security: {group} ===")
    ret, data = ctx.get_user_security(group)
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    # 添加股票到分组
    print(f"\n=== modify_user_security: ADD HK.00700 ===")
    ret, data = ctx.modify_user_security(
        group_name=group,
        op=ft.ModifyUserSecurityOp.ADD,
        code_list=["HK.00700"],
    )
    print("add ret:", ret, data)

    # 再次查看
    print(f"\n=== get_user_security after ADD ===")
    ret, data = ctx.get_user_security(group)
    if ret == 0:
        print(data.to_string())

    # 删除
    print(f"\n=== modify_user_security: DEL HK.00700 ===")
    ret, data = ctx.modify_user_security(
        group_name=group,
        op=ft.ModifyUserSecurityOp.DEL,
        code_list=["HK.00700"],
    )
    print("del ret:", ret, data)

    ctx.close()
