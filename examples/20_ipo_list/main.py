# -*- coding: utf-8 -*-
"""IPO列表 (get_ipo_list)

Demonstrates:
  - get_ipo_list: upcoming and recent IPOs for a market
  - Market types: HK, US
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
    logger.info("=== IPO List Demo ===")

    ctx = create_quote_context()

    try:
        for market, label in [(ft.Market.HK, "HK"), (ft.Market.US, "US")]:
            logger.info("\n=== get_ipo_list: %s ===", label)
            ret, data = ctx.get_ipo_list(market)
            if ret != 0:
                logger.error("get_ipo_list (%s) failed: %s", label, data)
            else:
                if data.empty:
                    logger.info("No IPO records for market %s", label)
                else:
                    logger.info("IPO records: %d | Columns: %s", len(data), list(data.columns))
                    for col in data.columns:
                        logger.info("  %-20s = %s", col, data[col].tolist())
                    logger.info("\nFirst 5 IPOs:\n%s", data.head(5).to_string())

    finally:
        ctx.close()
        logger.info("Done.")