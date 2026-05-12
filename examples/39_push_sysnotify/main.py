# -*- coding: utf-8 -*-
"""系统通知推送 (SysNotifyHandlerBase)

Demonstrates:
  - SysNotifyHandlerBase: real-time system notifications
  - on_recv callback with full notification data
  - Proper handler pattern with error handling
  - Logging of all notification fields
"""
import sys
import logging
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from futu import SysNotifyHandlerBase
from connect import create_trade_context, get_demo_trade_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


class MySysNotify(SysNotifyHandlerBase):
    def on_recv(self, rsp_str):
        ret, data = super().on_recv(rsp_str)
        if ret == 0:
            logger.info("[SysNotify] type=%s subtype=%s msg=%s", data.get("type"), data.get("sub_type"), data.get("msg"))
            # Log all available fields
            for k, v in data.items():
                logger.debug("  %s: %s", k, v)
            return ret, data
        logger.error("[SysNotify] error: %s", data)
        return ret, data


if __name__ == "__main__":
    logger.info("=== System Notification Push Demo ===")

    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)
    trd_ctx.set_handler(MySysNotify())

    try:
        pwd = get_demo_trade_password()
        ret, data = trd_ctx.unlock_trade(pwd)
        if ret != ft.RET_OK:
            logger.error("unlock_trade failed: %s", data)
            raise SystemExit(1)
        logger.info("unlock_trade: OK")
        logger.info("Listening for system notifications (10s)...")

        time.sleep(10)
        logger.info("Finished listening.")

    finally:
        trd_ctx.close()
        logger.info("Done.")