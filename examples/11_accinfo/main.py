# -*- coding: utf-8 -*-
"""账户资金查询 (accinfo_query / position_list_query)

Demonstrates:
  - accinfo_query: account cash, power, margin, etc.
  - position_list_query: all positions with qty, cost, P&L
  - Proper logging of all returned fields
"""
import sys
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context, create_trade_context, get_demo_trade_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("=== Account Info & Positions Demo ===")

    quote_ctx = create_quote_context()
    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)

    try:
        pwd = get_demo_trade_password()
        logger.info("Unlocking trade with SIMULATE password...")
        ret, data = trd_ctx.unlock_trade(pwd)
        if ret != ft.RET_OK:
            logger.error("unlock_trade failed: %s", data)
            raise SystemExit(1)
        logger.info("unlock_trade: OK")

        # ── Account Info ──────────────────────────────────────────────
        logger.info("\n=== accinfo_query ===")
        ret, data = trd_ctx.accinfo_query()
        if ret != ft.RET_OK:
            logger.error("accinfo_query failed: %s", data)
        else:
            logger.info("Account info (%d rows):", len(data))
            for col in data.columns:
                logger.info("  %s: %s", col, data[col].values[0])
            logger.info("\nFull DataFrame:\n%s", data.to_string())

        # ── Positions ──────────────────────────────────────────────────
        logger.info("\n=== position_list_query ===")
        ret, data = trd_ctx.position_list_query()
        if ret != ft.RET_OK:
            logger.error("position_list_query failed: %s", data)
        else:
            if data.empty:
                logger.info("No positions (empty portfolio)")
            else:
                logger.info("Positions (%d rows):", len(data))
                logger.info("Columns: %s", list(data.columns))
                for col in data.columns:
                    logger.info("  %s: %s", col, data[col].tolist())
                logger.info("\nFull DataFrame:\n%s", data.to_string())

    finally:
        quote_ctx.close()
        trd_ctx.close()
        logger.info("Done.")