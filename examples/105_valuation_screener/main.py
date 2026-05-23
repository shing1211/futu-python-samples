"""Valuation Screener — get_valuation_detail, get_valuation_plate_stock_list, get_stock_screen.

Demonstrates three valuation-related SDK APIs:
  - get_valuation_detail(code)
  - get_valuation_plate_stock_list(market, stock_type)
  - get_stock_screen(market, filter_list)

Usage:
    python3 main.py [--code HK.00700]
"""
import sys
import logging
import argparse

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from connect import create_quote_context
import futu as ft

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Valuation Screener")
    parser.add_argument("--code", default="HK.00700", help="Stock code")
    args = parser.parse_args()

    quote_ctx = create_quote_context()
    try:
        logger.info("=== Valuation Detail for %s ===", args.code)
        try:
            ret, df = quote_ctx.get_valuation_detail(args.code)
            if ret == ft.RetCode.SUCCESS and df is not None and not df.empty:
                print(df.to_string(index=False))
            else:
                logger.warning("No valuation detail: %s", df)
        except Exception as e:
            logger.warning("Valuation detail failed: %s", e)

        logger.info("=== Valuation Plate Stock List (HK) ===")
        try:
            ret, df = quote_ctx.get_valuation_plate_stock_list(ft.Market.HK, ft.SecurityType.STOCK)
            if ret == ft.RetCode.SUCCESS and df is not None and not df.empty:
                print(df.to_string(index=False))
            else:
                logger.warning("No plate stock list: %s", df)
        except Exception as e:
            logger.warning("Plate stock list failed: %s", e)

        logger.info("=== Stock Screen (HK) ===")
        try:
            ret, screen_data = quote_ctx.get_stock_screen(ft.Market.HK, [])
            if ret == ft.RetCode.SUCCESS:
                print(screen_data)
            else:
                logger.warning("Stock screen failed: %s", screen_data)
        except Exception as e:
            logger.warning("Stock screen error: %s", e)

    finally:
        quote_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()
