# -*- coding: utf-8 -*-
"""订单/成交推送 (TradeOrderHandlerBase / TradeDealHandlerBase)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from futu import TradeOrderHandlerBase, TradeDealHandlerBase
from connect import create_trade_context


class MyOrderHandler(TradeOrderHandlerBase):
    def on_recv(self, rsp_str):
        ret, data = super().on_recv(rsp_str)
        if ret == 0:
            print("[OrderUpdate]", data)


class MyDealHandler(TradeDealHandlerBase):
    def on_recv(self, rsp_str):
        ret, data = super().on_recv(rsp_str)
        if ret == 0:
            print("[DealUpdate]", data)


if __name__ == "__main__":
    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)
    trd_ctx.set_handler(MyOrderHandler())
    trd_ctx.set_handler(MyDealHandler())

    ret, data = trd_ctx.unlock_trade("123456")
    print("unlock:", ret, "OK" if ret == 0 else data)

    print("\nListening for order/deal pushes (5s)...")
    import time
    time.sleep(5)

    trd_ctx.close()
    print("Done")
