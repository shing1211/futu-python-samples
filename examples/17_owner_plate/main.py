# -*- coding: utf-8 -*-
"""所属板块 / 相关股票 (get_owner_plate / get_referencestock_list)

Demonstrates:
  - get_owner_plate: get industry/concept plates a stock belongs to
  - get_referencestock_list: warrant/bull-bear reference stocks
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
    logger.info("=== Owner Plate & Reference Stock Demo ===")

    ctx = create_quote_context()

    try:
        code = "HK.00700"

        # ── get_owner_plate ─────────────────────────────────────────────
        logger.info("\n=== get_owner_plate: %s ===", code)
        ret, data = ctx.get_owner_plate([code])
        if ret != 0:
            logger.error("get_owner_plate failed: %s", data)
        else:
            logger.info("Plates (%d):", len(data))
            logger.info("Columns: %s", list(data.columns))
            for _, row in data.iterrows():
                logger.info("  code=%s name=%s plate_type=%s",
                            row.get("code"), row.get("name"),
                            row.get("plate_type", "?"))
            logger.info("\n%s", data.to_string())

        # ── get_referencestock_list: warrants ─────────────────────────────
        logger.info("\n=== get_referencestock_list: %s [WARRANT] ===", code)
        ret, data = ctx.get_referencestock_list(code, ft.SecurityReferenceType.WARRANT)
        if ret != 0:
            logger.error("get_referencestock_list (WARRANT) failed: %s", data)
        else:
            logger.info("Warrant reference stocks (%d):", len(data))
            if not data.empty:
                logger.info("Columns: %s", list(data.columns))
                for _, row in data.head(5).iterrows():
                    logger.info("  code=%s name=%s", row.get("code"), row.get("name"))
                logger.info("\n%s", data.head(5).to_string())

        # ── get_referencestock_list: bull/bear ────────────────────────────
        logger.info("\n=== get_referencestock_list: %s [BULL_BEAR] ===", code)
        ret, data = ctx.get_referencestock_list(code, ft.SecurityReferenceType.BULL_BEAR)
        if ret != 0:
            logger.error("get_referencestock_list (BULL_BEAR) failed: %s", data)
        else:
            logger.info("Bull/Bear reference stocks (%d):", len(data))
            if not data.empty:
                logger.info("Columns: %s", list(data.columns))
                for _, row in data.head(5).iterrows():
                    logger.info("  code=%s name=%s", row.get("code"), row.get("name"))
                logger.info("\n%s", data.head(5).to_string())

    finally:
        ctx.close()
        logger.info("Done.")