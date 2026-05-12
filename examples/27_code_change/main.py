# -*- coding: utf-8 -*-
"""股票代码变更查询 (get_code_change)

Demonstrates:
  - get_code_change: find historical stock code changes
  - Useful for tracking delisted/renamed/merged stocks
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
    logger.info("=== Stock Code Change Demo ===")

    ctx = create_quote_context()

    try:
        codes = ["HK.00700", "HK.00005", "US.AAPL"]

        logger.info("\n=== get_code_change: %s ===", codes)
        ret, data = ctx.get_code_change(code_list=codes)
        if ret != 0:
            logger.error("get_code_change failed: %s", data)
        else:
            if data.empty:
                logger.info("No code changes found for %s", codes)
            else:
                logger.info("Code change records: %d | Columns: %s", len(data), list(data.columns))
                for col in data.columns:
                    logger.info("  %-20s = %s", col, data[col].tolist())
                logger.info("\n%s", data.to_string())

    finally:
        ctx.close()
        logger.info("Done.")