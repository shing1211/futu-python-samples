# -*- coding: utf-8 -*-
"""实时K线推送 (CurKlineHandlerBase)

Demonstrates:
  - CurKlineHandlerBase: real-time K-line bar updates
  - subscribe: subscribe to K_DAY, K_30M, K_1H, etc.
  - on_recv_rsp: handle push callback with full bar data
  - All K-line fields: open, high, low, close, volume, time_key

Note: Push is continuous. Run with time.sleep() to observe live updates.
"""
import logging
import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from futu import CurKlineHandlerBase, RET_OK
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


class MyKlineHandler(CurKlineHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, kline_list = super().on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            logger.error("Kline push error: %s", kline_list)
            return ret_code, kline_list
        for k in kline_list:
            logger.info("[Kline] code=%s time=%s O=%.2f H=%.2f L=%.2f C=%.2f vol=%d",
                        k.code, k.time_key, k.open, k.high, k.low, k.close, k.volume)
        return RET_OK, kline_list


if __name__ == "__main__":
    logger.info("=== Real-time K-line Push Demo ===")

    ctx = create_quote_context()
    ctx.set_handler(MyKlineHandler())

    try:
        code = "HK.00700"

        for ktype_label, ktype in [
            ("K_DAY (daily)", ft.SubType.K_DAY),
            ("K_30M", ft.SubType.K_30M),
        ]:
            ret, _ = ctx.subscribe(code, ktype)
            logger.info("subscribe ret=%d code=%s type=%s", ret, code, ktype_label)

        logger.info("Watching %s K-line pushes for 15 seconds...", code)
        time.sleep(15)
        logger.info("Finished.")

    finally:
        ctx.close()
        logger.info("Done.")