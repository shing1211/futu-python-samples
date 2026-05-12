# -*- coding: utf-8 -*-
"""实时K线推送 (CurKlineHandlerBase)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from futu import CurKlineHandlerBase, RET_OK
from connect import create_quote_context


class MyKlineHandler(CurKlineHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, kline_list = super().on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            print("Kline push error:", kline_list)
            return ret_code, kline_list
        for k in kline_list:
            print(f"  {k.code} | {k.time_key} | O={k.open} H={k.high} L={k.low} C={k.close} vol={k.volume}")
        return RET_OK, kline_list


if __name__ == "__main__":
    ctx = create_quote_context()
    ctx.set_handler(MyKlineHandler())

    # 订阅日K线实时推送
    code = "HK.00700"
    ret = ctx.subscribe(code, ft.SubType.K_DAY)
    print("subscribe ret:", ret)
    print("Watching", code, "K_DAY push for 10 seconds...")

    import time
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        pass
    finally:
        ctx.close()
