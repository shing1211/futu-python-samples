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
    elif isinstance(data, list):
        logger.info("%s list[%d]: %s", label, len(data), str(data)[:500])
    else:
        logger.info("%s: %s", label, data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Financial Statements Demo")
    parser.add_argument("--code", default="HK.00700", help="Stock code")
    args = parser.parse_args()

    code = args.code
    logger.info("=== Financial Statements Demo: %s ===", code)

    ctx = create_quote_context()

    try:
        logger.info("=== get_financials_statements ===")
        try:
            show("get_financials_statements", *ctx.get_financials_statements(code, 0, 0))
        except Exception as e:
            logger.error("get_financials_statements: %s", e)

        logger.info("=== get_financials_revenue_breakdown ===")
        try:
            show("get_financials_revenue_breakdown", *ctx.get_financials_revenue_breakdown(code))
        except Exception as e:
            logger.error("get_financials_revenue_breakdown: %s", e)

        logger.info("=== get_financials_earnings_price_move ===")
        try:
            show("get_financials_earnings_price_move", *ctx.get_financials_earnings_price_move(code))
        except Exception as e:
            logger.error("get_financials_earnings_price_move: %s", e)

        logger.info("=== get_financials_earnings_price_history ===")
        try:
            show("get_financials_earnings_price_history", *ctx.get_financials_earnings_price_history(code))
        except Exception as e:
            logger.error("get_financials_earnings_price_history: %s", e)

    finally:
        ctx.close()
        logger.info("Done.")
