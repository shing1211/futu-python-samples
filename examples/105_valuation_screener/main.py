# -*- coding: utf-8 -*-
import logging
import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def show(label, ret, data):
    if ret != 0:
        logger.warning("%s ret=%d msg=%s", label, ret, data)
        return
    if data is None:
        logger.warning("%s returned None", label)
        return
    if hasattr(data, "to_string"):
        logger.info("%s DataFrame:\n%s", label, data.to_string())
    elif isinstance(data, dict):
        import json
        logger.info("%s dict:\n%s", label, json.dumps(data, indent=2, ensure_ascii=False, default=str)[:2000])
    else:
        logger.info("%s: %s", label, data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Valuation Screener")
    parser.add_argument("--code", default="HK.00700", help="Stock code")
    args = parser.parse_args()

    logger.info("=== Valuation Screener: %s ===", args.code)

    quote_ctx = create_quote_context()
    try:
        logger.info("=== get_valuation_detail ===")
        try:
            show("get_valuation_detail", *quote_ctx.get_valuation_detail(args.code))
        except Exception as e:
            logger.warning("get_valuation_detail: %s", e)

        logger.info("=== get_valuation_plate_stock_list ===")
        try:
            show("get_valuation_plate_stock_list", *quote_ctx.get_valuation_plate_stock_list(args.code))
        except Exception as e:
            logger.warning("get_valuation_plate_stock_list: %s", e)

        logger.info("=== get_stock_screen ===")
        try:
            req = ft.StockScreenRequest()
            req.add_simple_property(ft.SimpleProperty.PRICE)
            req.add_simple_property(ft.SimpleProperty.CHANGE_5MIN)
            req.page_from = 0
            req.page_count = 10
            show("get_stock_screen", *quote_ctx.get_stock_screen(req))
        except Exception as e:
            logger.warning("get_stock_screen: %s", e)

    finally:
        quote_ctx.close()
        logger.info("Done.")
