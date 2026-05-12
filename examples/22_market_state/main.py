# -*- coding: utf-8 -*-
"""市场状态 (get_market_state) — 盘前/盘中/盘后/Closed

Demonstrates:
  - get_market_state: check trading session status for multiple stocks
  - Market states: PRE_OPEN, OPEN, AFTER, CLOSED
  - Cross-market: HK, US, SH, SZ stocks
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
    logger.info("=== Market State (Trading Session) Demo ===")

    ctx = create_quote_context()

    try:
        codes = ["HK.00700", "US.AAPL", "SH.600000", "SZ.000001"]

        logger.info("\n=== get_market_state: %s ===", codes)
        ret, data = ctx.get_market_state(codes)
        if ret != 0:
            logger.error("get_market_state failed: %s", data)
        else:
            logger.info("Retrieved %d records | Columns: %s", len(data), list(data.columns))
            for col in data.columns:
                logger.info("  %-20s = %s", col, data[col].tolist())
            logger.info("\n%s", data.to_string())

    finally:
        ctx.close()
        logger.info("Done.")