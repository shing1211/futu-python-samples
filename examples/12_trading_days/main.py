# -*- coding: utf-8 -*-
"""交易日历 (request_trading_days)

Demonstrates:
  - request_trading_days: get trading days for a market in a date range
  - Market types: HK, US, SH, SZ
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
    logger.info("=== Trading Days (Calendar) Demo ===")

    ctx = create_quote_context()

    try:
        for market, label in [
            (ft.Market.HK, "HK"),
            (ft.Market.US, "US"),
            (ft.Market.SH, "SH"),
            (ft.Market.SZ, "SZ"),
        ]:
            logger.info("\n=== request_trading_days: %s (2026-04 to 2026-05) ===", label)
            ret, data = ctx.request_trading_days(market, "2026-04-01", "2026-05-31")
            if ret != 0:
                logger.error("request_trading_days (%s) failed: %s", label, data)
            else:
                logger.info("Trading days (%d): %s", len(data), data)
                logger.info("Type: %s | Shape: %s", type(data), data.shape if hasattr(data, 'shape') else 'N/A')

    finally:
        ctx.close()
        logger.info("Done.")