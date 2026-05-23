# -*- coding: utf-8 -*-
"""公司行动 (get_corporate_actions_dividends / buybacks / stock_splits)

Demonstrates:
  - get_corporate_actions_dividends: corporate dividend data
  - get_corporate_actions_buybacks: buyback data
  - get_corporate_actions_stock_splits: stock split data
  - Each API call wrapped in try/except for resilience
"""
import argparse
import logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("=== Corporate Actions Demo ===")

    parser = argparse.ArgumentParser()
    parser.add_argument("--code", default="HK.00700", help="Stock code")
    args = parser.parse_args()

    code = args.code
    ctx = create_quote_context()

    try:
        # ── Dividends ────────────────────────────────────────────────────
        logger.info("\n=== get_corporate_actions_dividends(%s) ===", code)
        try:
            ret, data = ctx.get_corporate_actions_dividends(code)
            if ret != 0:
                logger.error("get_corporate_actions_dividends failed: %s", data)
            elif data is not None and not data.empty:
                logger.info("Dividends DataFrame:\n%s", data.to_string())
            else:
                logger.info("No dividend data returned.")
        except Exception as e:
            logger.exception("get_corporate_actions_dividends error: %s", e)

        # ── Buybacks ─────────────────────────────────────────────────────
        logger.info("\n=== get_corporate_actions_buybacks(%s) ===", code)
        try:
            ret, data = ctx.get_corporate_actions_buybacks(code)
            if ret != 0:
                logger.error("get_corporate_actions_buybacks failed: %s", data)
            elif data is not None and not data.empty:
                logger.info("Buybacks DataFrame:\n%s", data.to_string())
            else:
                logger.info("No buyback data returned.")
        except Exception as e:
            logger.exception("get_corporate_actions_buybacks error: %s", e)

        # ── Stock Splits ─────────────────────────────────────────────────
        logger.info("\n=== get_corporate_actions_stock_splits(%s) ===", code)
        try:
            ret, data = ctx.get_corporate_actions_stock_splits(code)
            if ret != 0:
                logger.error("get_corporate_actions_stock_splits failed: %s", data)
            elif data is not None and not data.empty:
                logger.info("Stock Splits DataFrame:\n%s", data.to_string())
            else:
                logger.info("No stock split data returned.")
        except Exception as e:
            logger.exception("get_corporate_actions_stock_splits error: %s", e)

    finally:
        ctx.close()
        logger.info("Done.")
