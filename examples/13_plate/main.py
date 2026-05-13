# -*- coding: utf-8 -*-
"""板块列表 (get_plate_list / get_plate_stock)

Demonstrates:
  - get_plate_list: all industry/sector plates for a market
  - Plate types: ALL, INDUSTRY, concept, etc.
  - get_plate_stock: stocks belonging to a specific plate
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
    logger.info("=== Plate (Sector) List Demo ===")

    ctx = create_quote_context()

    try:
        for plate_type, type_label in [
            (ft.Plate.ALL, "ALL"),
            (ft.Plate.INDUSTRY, "INDUSTRY"),
        ]:
            logger.info("\n=== get_plate_list: HK (type=%s) ===", type_label)
            ret, data = ctx.get_plate_list(ft.Market.HK, plate_type)
            if ret != 0:
                logger.error("get_plate_list (%s) failed: %s", type_label, data)
            else:
                logger.info("Total plates: %d | Columns: %s", len(data), list(data.columns))
                logger.info("First 5 plates:")
                for _, row in data.head(5).iterrows():
                    logger.info("  code=%s name=%s plate_type=%s",
                                row.get("code"), row.get("name"), row.get("plate_type", type_label))
                logger.info("\n%s", data.head(10).to_string())

        # ── Get stocks in a specific plate ─────────────────────────────
        logger.info("\n=== get_plate_list: HK (INDUSTRY) ===")
        ret, plates = ctx.get_plate_list(ft.Market.HK, ft.Plate.INDUSTRY)
        if ret == 0 and not plates.empty:
            first_plate = plates.iloc[0]['code']
            first_name = plates.iloc[0]['plate_name']
            logger.info("\n=== get_plate_stock: %s (%s) ===", first_name, first_plate)

            ret2, stock_list = ctx.get_plate_stock(first_plate)
            if ret2 != 0:
                logger.error("get_plate_stock failed: %s", stock_list)
            else:
                logger.info("Stocks in plate '%s': %d | Columns: %s",
                            first_name, len(stock_list), list(stock_list.columns))
                for _, row in stock_list.head(5).iterrows():
                    logger.info("  code=%s name=%s list_time=%s",
                                row.get("code"), row.get("name"),
                                row.get("list_time", "?"))
                logger.info("\n%s", stock_list.head(10).to_string())

    finally:
        ctx.close()
        logger.info("Done.")