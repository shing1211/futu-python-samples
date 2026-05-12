# -*- coding: utf-8 -*-
"""股票基本信息 (get_stock_basicinfo)

Demonstrates:
  - get_stock_basicinfo: fetch basic info for stocks by market or code list
  - SecurityType: STOCK, IDX, ETF, WARRANT, BOND, FUTURE, OPTION
  - Query by market + type, or by specific code list
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
    logger.info("=== Stock Basic Info Demo ===")

    ctx = create_quote_context()

    try:
        # ── By market + type (HK stocks, first 5) ─────────────────────────
        logger.info("\n=== get_stock_basicinfo: HK STOCK (first 5) ===")
        ret, data = ctx.get_stock_basicinfo(
            market=ft.Market.HK,
            stock_type=ft.SecurityType.STOCK,
        )
        if ret != 0:
            logger.error("get_stock_basicinfo (market) failed: %s", data)
        else:
            logger.info("Total HK stocks: %d | Columns: %s", len(data), list(data.columns))
            logger.info("First 5 stocks:")
            for _, row in data.head(5).iterrows():
                logger.info("  code=%s name=%s stock_type=%s lot_size=%s",
                            row.get("code"), row.get("name"),
                            row.get("type", row.get("stock_type", "?")),
                            row.get("lot_size", "?"))
            logger.info("\n%s", data.head(5).to_string())

        # ── By specific code list ────────────────────────────────────────
        codes = ["HK.00700", "HK.00005", "HK.HSImain", "US.AAPL", "SH.600000"]
        logger.info("\n=== get_stock_basicinfo: specific codes=%s ===", codes)
        ret, data = ctx.get_stock_basicinfo(
            market=ft.Market.HK,
            code_list=codes,
        )
        if ret != 0:
            logger.error("get_stock_basicinfo (code_list) failed: %s", data)
        else:
            logger.info("Retrieved %d stocks | Columns: %s", len(data), list(data.columns))
            for _, row in data.iterrows():
                logger.info("  code=%s name=%s market=%s type=%s",
                            row.get("code"), row.get("name"),
                            row.get("market", "?"), row.get("type", "?"))
            logger.info("\n%s", data.to_string())

    finally:
        ctx.close()
        logger.info("Done.")