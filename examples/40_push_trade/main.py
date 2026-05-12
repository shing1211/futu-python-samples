# -*- coding: utf-8 -*-
"""订单/成交推送 (TradeOrderHandlerBase / TradeDealHandlerBase)

Demonstrates:
  - TradeOrderHandlerBase: live order status updates
  - TradeDealHandlerBase: trade execution notifications
  - on_recv callbacks with full payload logging
  - Handler registration with set_handler
  - Logging of all returned fields
"""
import sys
import logging
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from futu import TradeOrderHandlerBase, TradeDealHandlerBase
from connect import create_trade_context, get_demo_trade_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


class MyOrderHandler(TradeOrderHandlerBase):
    def on_recv(self, rsp_str):
        ret, data = super().on_recv(rsp_str)
        if ret == 0:
            logger.info("[OrderUpdate] ret=OK data=%s", data)
            if isinstance(data, dict):
                for k, v in data.items():
                    logger.info("  %-20s = %s", k, v)
            elif hasattr(data, "__dict__"):
                logger.info("  %s", data.__dict__)
        else:
            logger.error("[OrderUpdate] error: %s", data)
        return ret, data


class MyDealHandler(TradeDealHandlerBase):
    def on_recv(self, rsp_str):
        ret, data = super().on_recv(rsp_str)
        if ret == 0:
            logger.info("[DealUpdate] ret=OK data=%s", data)
            if isinstance(data, dict):
                for k, v in data.items():
                    logger.info("  %-20s = %s", k, v)
            elif hasattr(data, "__dict__"):
                logger.info("  %s", data.__dict__)
        else:
            logger.error("[DealUpdate] error: %s", data)
        return ret, data


if __name__ == "__main__":
    logger.info("=== Trade Order & Deal Push Demo ===")

    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)
    trd_ctx.set_handler(MyOrderHandler())
    trd_ctx.set_handler(MyDealHandler())

    try:
        pwd = get_demo_trade_password()
        ret, data = trd_ctx.unlock_trade(pwd)
        if ret != ft.RET_OK:
            logger.error("unlock_trade failed: %s", data)
            raise SystemExit(1)
        logger.info("unlock_trade: OK")
        logger.info("Listening for order/deal pushes (10s)...")
        logger.info("Place an order in SIMULATE mode to trigger pushes...")

        time.sleep(10)
        logger.info("Finished listening.")

    finally:
        trd_ctx.close()
        logger.info("Done.")