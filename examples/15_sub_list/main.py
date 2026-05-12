# -*- coding: utf-8 -*-
"""查询已订阅列表 (query_subscription / unsubscribe)

Demonstrates:
  - subscribe: subscribe to multiple stock+subtype combos
  - query_subscription: list all active subscriptions
  - unsubscribe: remove specific subscriptions
  - unsubscribe_all: clear all subscriptions
  - All returned fields logged
"""
import logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("=== Subscription Management Demo ===")

    ctx = create_quote_context()

    try:
        codes = ["HK.00700", "HK.HSImain", "US.AAPL", "SH.600000"]
        subtypes = [ft.SubType.QUOTE, ft.SubType.K_DAY, ft.SubType.ORDER_BOOK, ft.SubType.BROKER]

        logger.info("Subscribing to %s codes x %s subtypes...", len(codes), len(subtypes))
        ret = ctx.subscribe(codes, subtypes)
        logger.info("subscribe ret=%d", ret)

        # ── Query active subscriptions ───────────────────────────────────
        logger.info("\n=== query_subscription (all connections) ===")
        ret, data = ctx.query_subscription(is_all_conn=True)
        if ret != 0:
            logger.error("query_subscription failed: %s", data)
        else:
            logger.info("Subscription data type: %s", type(data))
            if isinstance(data, dict):
                for k, v in data.items():
                    logger.info("  %s: %s", k, v)
            elif hasattr(data, 'to_string'):
                logger.info("Full:\n%s", data.to_string())
            else:
                logger.info("Data: %s", data)

        # ── Also check per-connection ──────────────────────────────────────
        logger.info("\n=== query_subscription (current conn only) ===")
        ret, data2 = ctx.query_subscription(is_all_conn=False)
        logger.info("ret=%d data=%s", ret, data2)

        # ── Unsubscribe specific subtype ───────────────────────────────────
        logger.info("\n=== unsubscribe: K_DAY from HK.00700 ===")
        ret = ctx.unsubscribe(codes=['HK.00700'], subtype_list=[ft.SubType.K_DAY])
        logger.info("unsubscribe ret=%d", ret)

        # ── Re-query ───────────────────────────────────────────────────────
        logger.info("\n=== query_subscription after unsubscribe ===")
        ret, data3 = ctx.query_subscription(is_all_conn=False)
        logger.info("ret=%d data=%s", ret, data3)

        # ── Unsubscribe all ────────────────────────────────────────────────
        logger.info("\n=== unsubscribe_all ===")
        ret = ctx.unsubscribe_all()
        logger.info("unsubscribe_all ret=%d", ret)

        # ── Final check ───────────────────────────────────────────────────
        logger.info("\n=== query_subscription after unsubscribe_all ===")
        ret, data4 = ctx.query_subscription(is_all_conn=False)
        logger.info("ret=%d data=%s", ret, data4)

    finally:
        ctx.close()
        logger.info("Done.")