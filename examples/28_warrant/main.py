# -*- coding: utf-8 -*-
"""窝轮/涡轮数据 (get_warrant)

Demonstrates:
  - get_warrant: list all warrants (structured products) for an underlying
  - Warrant data: strike, expiry, premium, effective leverage, etc.
  - All returned fields logged

Warrants (窝轮/涡轮) are derivative instruments issued by banks against stocks.
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
    logger.info("=== Warrant Data Demo ===")

    ctx = create_quote_context()

    try:
        for owner in ["HK.00700", "HK.HSImain"]:
            logger.info("\n=== get_warrant: owner=%s ===", owner)
            ret, data = ctx.get_warrant(stock_owner=owner)
            if ret != 0:
                logger.error("get_warrant failed: %s", data)
            else:
                if data.empty:
                    logger.info("No warrants found for %s", owner)
                else:
                    logger.info("Total warrants: %d | Columns: %s", len(data), list(data.columns))
                    for col in data.columns:
                        vals = data[col].tolist()[:5]
                        logger.info("  %-25s = %s", col, vals)
                    logger.info("\nFirst 5 warrants:\n%s", data.head(5).to_string())

    finally:
        ctx.close()
        logger.info("Done.")