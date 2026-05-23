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
    parser = argparse.ArgumentParser(description="Option Analytics")
    parser.add_argument("--code", default="US.AAPL260616C200000", help="Option contract code")
    parser.add_argument("--underlying", default="US.AAPL", help="Underlying stock code")
    args = parser.parse_args()

    quote_ctx = create_quote_context()
    try:
        logger.info("=== get_option_volatility ===")
        try:
            show("get_option_volatility", *quote_ctx.get_option_volatility(args.code))
        except Exception as e:
            logger.warning("get_option_volatility: %s", e)

        logger.info("=== get_option_exercise_probability ===")
        try:
            show("get_option_exercise_probability", *quote_ctx.get_option_exercise_probability(args.code))
        except Exception as e:
            logger.warning("get_option_exercise_probability: %s", e)

        logger.info("=== get_option_screen ===")
        try:
            req = ft.OptionScreenRequest([ft.OptMarketCategory.US_STOCK])
            show("get_option_screen", *quote_ctx.get_option_screen(req))
        except Exception as e:
            logger.warning("get_option_screen: %s", e)

    finally:
        quote_ctx.close()
        logger.info("Done.")
