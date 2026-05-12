# -*- coding: utf-8 -*-
"""相关股票列表 (get_referencestock_list)

Demonstrates:
  - get_referencestock_list: get related warrant/bull-bear reference stocks
  - SecurityReferenceType: WARRANT, BULL_BEAR
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
        for code in ["HK.00700", "US.AAPL"]:
            logger.info("\n=== Processing %s ===", code)

            for ref_type, type_label in [
                (ft.SecurityReferenceType.WARRANT, "WARRANT"),
                (ft.SecurityReferenceType.BULL_BEAR, "BULL_BEAR"),
            ]:
                logger.info("\n  --- get_referencestock_list: %s [%s] ---", code, type_label)
                ret, data = ctx.get_referencestock_list(code, ref_type)
                if ret != 0:
                    logger.error("get_referencestock_list failed: %s", data)
                else:
                    if data.empty:
                        logger.info("  No reference stocks found for type=%s", type_label)
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