# -*- coding: utf-8 -*-
"""获取经纪队列 (get_broker_queue)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    code = "HK.00700"

    # 订阅买卖经纪队列
    ret = ctx.subscribe(code, ft.SubType.BROKER)
    print("subscribe ret:", ret)

    # 获取经纪队列
    print("\n=== get_broker_queue ===")
    ret, bid_data, ask_data = ctx.get_broker_queue(code)
    if ret == 0:
        print("BID (经纪买):")
        print(bid_data.to_string())
        print("\nASK (经纪卖):")
        print(ask_data.to_string())
    else:
        print("error:", bid_data)

    ctx.close()
