# -*- coding: utf-8 -*-
"""期货合约信息 (get_future_info)

Demonstrates:
  - get_future_info: fetch contract specifications for futures
  - Multi-future: HK.HSImain (HSI), US.NQmain (Nasdaq futures)
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
    logger.info("=== Future Info Demo ===")

    ctx = create_quote_context()

    try:
        codes = ["HK.HSImain", "US.NQmain"]

        logger.info("\n=== get_future_info: %s ===", codes)
        ret, data = ctx.get_future_info(codes)
        if ret != 0:
            logger.error("get_future_info failed: %s", data)
        else:
            logger.info("Retrieved %d futures | Columns: %s", len(data), list(data.columns))
            for _, row in data.iterrows():
                logger.info("\n  === %s (%s) ===", row.get("code", "?"), row.get("name", "?"))
                for col in data.columns:
                    logger.info("    %-25s = %s", col, row.get(col, "?"))
            logger.info("\nFull DataFrame:\n%s", data.to_string())

    finally:
        ctx.close()
        logger.info("Done.")