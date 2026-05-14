# -*- coding: utf-8 -*-
"""经纪队列 (get_broker_queue)

Demonstrates:
  - subscribe: subscribe to broker queue subtype
  - get_broker_queue: fetch current broker bid/ask queue
  - Broker data: top N brokers with their bid/ask volumes
  - All returned fields logged

Broker queue shows which brokerage firms are at the bid/ask.
This is useful for understanding institutional order flow.
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
    logger.info("=== Broker Queue Demo ===")

    ctx = create_quote_context()

    try:
        code = "HK.00700"

        ret, _ = ctx.subscribe(code, ft.SubType.BROKER)
        logger.info("subscribe ret=%d code=%s", ret, code)

        # ── get_broker_queue ─────────────────────────────────────────────
        logger.info("\n=== get_broker_queue: %s ===", code)
        ret, (bid_data, ask_data) = ctx.get_broker_queue(code)
        if ret != 0:
            logger.error("get_broker_queue failed: bid_data=%s", bid_data)
        else:
            logger.info("\nBID Brokers (%d entries):", len(bid_data) if bid_data else 0)
            if bid_data:
                logger.info("Columns: %s", list(bid_data.columns) if hasattr(bid_data, 'columns') else "N/A")
                for _, row in bid_data.iterrows():
                    logger.info("  broker_id=%s name=%s bid_price=%.2f bid_vol=%d",
                                row.get("broker_id", "?"), row.get("name", "?"),
                                row.get("bid_price", 0), row.get("bid_vol", 0))
                logger.info("\n%s", bid_data.to_string())

            logger.info("\nASK Brokers (%d entries):", len(ask_data) if ask_data else 0)
            if ask_data:
                logger.info("Columns: %s", list(ask_data.columns) if hasattr(ask_data, 'columns') else "N/A")
                for _, row in ask_data.iterrows():
                    logger.info("  broker_id=%s name=%s ask_price=%.2f ask_vol=%d",
                                row.get("broker_id", "?"), row.get("name", "?"),
                                row.get("ask_price", 0), row.get("ask_vol", 0))
                logger.info("\n%s", ask_data.to_string())

        # ── Also try with HK.HSImain (index) ────────────────────────────
        code2 = "HK.HSImain"
        logger.info("\n=== get_broker_queue: %s ===", code2)
        ret2, _ = ctx.subscribe(code2, ft.SubType.BROKER)
        logger.info("subscribe ret=%d", ret2)
        ret2, data2 = ctx.get_broker_queue(code2)
        if ret2 != 0:
            logger.error("get_broker_queue (%s) failed: %s", code2, data2)
        else:
            bid2, ask2 = data2 if isinstance(data2, tuple) and len(data2) == 2 else (data2, None)
            bid_len = len(bid2) if bid2 is not None and not bid2.empty else 0
            ask_len = len(ask2) if ask2 is not None and not ask2.empty else 0
            logger.info("%s BID brokers: %d | ASK brokers: %d", code2, bid_len, ask_len)

    finally:
        ctx.close()
        logger.info("Done.")