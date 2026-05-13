# -*- coding: utf-8 -*-
"""相关股票列表 (get_referencestock_list)

Demonstrates:
  - get_referencestock_list: get related warrant/bull-bear reference stocks
  - SecurityReferenceType: WARRANT, BULL_BEAR (BULL_BEAR may not exist in all SDK versions)
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
    logger.info("=== Reference Stock List Demo ===")

    ctx = create_quote_context()

    try:
        # Note: BULL_BEAR may not exist in all SDK versions; detect gracefully.
        try:
            bull_bear_type = ft.SecurityReferenceType.BULL_BEAR
            has_bull_bear = True
        except AttributeError:
            bull_bear_type = None
            has_bull_bear = False
            logger.info("SecurityReferenceType.BULL_BEAR not available in this SDK version")

        for code in ["HK.00700", "US.AAPL"]:
            logger.info("\n=== Processing %s ===", code)

            # WARRANT
            logger.info("\n  --- get_referencestock_list: %s [WARRANT] ---", code)
            ret, data = ctx.get_referencestock_list(code, ft.SecurityReferenceType.WARRANT)
            if ret != 0:
                logger.error("get_referencestock_list failed: %s", data)
            else:
                if data.empty:
                    logger.info("  No reference stocks found for type=WARRANT")
                else:
                    logger.info("  Count: %d | Columns: %s", len(data), list(data.columns))
                    for _, row in data.iterrows():
                        logger.info("    code=%s name=%s stock_type=%s",
                                    row.get("code"), row.get("name"),
                                    row.get("stock_type", "?"))
                    logger.info("\n  %s", data.to_string())

            # BULL_BEAR (if available)
            if has_bull_bear:
                logger.info("\n  --- get_referencestock_list: %s [BULL_BEAR] ---", code)
                ret, data = ctx.get_referencestock_list(code, bull_bear_type)
                if ret != 0:
                    logger.error("get_referencestock_list failed: %s", data)
                else:
                    if data.empty:
                        logger.info("  No reference stocks found for type=BULL_BEAR")
                    else:
                        logger.info("  Count: %d | Columns: %s", len(data), list(data.columns))
                        for _, row in data.iterrows():
                            logger.info("    code=%s name=%s stock_type=%s",
                                        row.get("code"), row.get("name"),
                                        row.get("stock_type", "?"))
                        logger.info("\n  %s", data.to_string())

    finally:
        ctx.close()
        logger.info("Done.")
