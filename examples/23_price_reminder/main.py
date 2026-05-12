# -*- coding: utf-8 -*-
"""价格提醒 (set_price_reminder / get_price_reminder)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    code = "HK.00700"

    # 设置价格提醒 — 当价格超过500时提醒
    print(f"=== set_price_reminder: {code} above 500 ===")
    ret, data = ctx.set_price_reminder(
        code=code,
        op=ft.PriceReminderOp.ADD,
        key="above_500",
        reminder_type=ft.PriceReminderType.PRICE_UP,
        reminder_freq=ft.PriceReminderFreq.ONCE,
        value=500.0,
        note="TCEH above 500!",
    )
    print("set ret:", ret, data)

    # 查询所有价格提醒
    print("\n=== get_price_reminder ===")
    ret, data = ctx.get_price_reminder(code=code)
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    # 删除刚加的提醒
    print("\n=== delete price reminder ===")
    ret, data = ctx.set_price_reminder(
        code=code,
        op=ft.PriceReminderOp.DEL,
        key="above_500",
    )
    print("delete ret:", ret, data)

    ctx.close()
