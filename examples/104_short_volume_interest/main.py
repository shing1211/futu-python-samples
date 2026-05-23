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
    parser = argparse.ArgumentParser(description="Short Volume & Interest Demo")
    parser.add_argument("--code", default="US.NVDA", help="Stock code")
    args = parser.parse_args()

    code = args.code
    logger.info("=== Short Volume & Interest Demo: %s ===", code)

    ctx = create_quote_context()

    try:
        logger.info("=== get_short_interest ===")
        try:
            ret, data, _ = ctx.get_short_interest(code)
            show("get_short_interest", ret, data)
        except Exception as e:
            logger.error("get_short_interest: %s", e)

        logger.info("=== get_daily_short_volume ===")
        try:
            ret, data, _ = ctx.get_daily_short_volume(code)
            show("get_daily_short_volume", ret, data)
        except Exception as e:
            logger.error("get_daily_short_volume: %s", e)

        logger.info("=== get_top_ten_buy_sell_brokers ===")
        try:
            show("get_top_ten_buy_sell_brokers", *ctx.get_top_ten_buy_sell_brokers(code))
        except Exception as e:
            logger.error("get_top_ten_buy_sell_brokers: %s", e)

    finally:
        ctx.close()
        logger.info("Done.")
