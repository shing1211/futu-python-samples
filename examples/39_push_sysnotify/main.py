# -*- coding: utf-8 -*-
"""系统通知推送 (SysNotifyHandlerBase)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from futu import SysNotifyHandlerBase
from connect import create_trade_context


class MySysNotify(SysNotifyHandlerBase):
    def on_recv(self, rsp_str):
        ret, data = super().on_recv(rsp_str)
        if ret == 0:
            print("[SysNotify]", data)


if __name__ == "__main__":
    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)
    trd_ctx.set_handler(MySysNotify())

    ret, data = trd_ctx.unlock_trade("123456")
    print("unlock:", ret, "OK" if ret == 0 else data)

    print("\nListening for system notifications (5s)...")
    import time
    time.sleep(5)

    trd_ctx.close()
    print("Done")
