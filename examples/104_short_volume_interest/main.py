# -*- coding: utf-8 -*-
"""做空成交量与兴趣 (get_short_interest / get_daily_short_volume / get_top_ten_buy_sell_brokers)

Demonstrates:
  - get_short_interest: short interest data
  - get_daily_short_volume: daily short volume
  - get_top_ten_buy_sell_brokers: top 10 buy/sell brokers
  - Each API call wrapped in try/except for resilience
"""
import argparse
import logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("=== Short Volume & Interest Demo ===")

    parser = argparse.ArgumentParser()
    parser.add_argument("--code", default="US.NVDA", help="Stock code")
    args = parser.parse_args()

    code = args.code
    ctx = create_quote_context()

    try:
        # ── Short Interest ───────────────────────────────────────────────
        logger.info("\n=== get_short_interest(%s) ===", code)
        try:
            ret, data = ctx.get_short_interest(code)
            if ret != 0:
                logger.error("get_short_interest failed: %s", data)
            elif data is not None and not data.empty:
                logger.info("Short Interest DataFrame:\n%s", data.to_string())
            else:
                logger.info("No short interest data returned.")
        except Exception as e:
            logger.exception("get_short_interest error: %s", e)

        # ── Daily Short Volume ───────────────────────────────────────────
        logger.info("\n=== get_daily_short_volume(%s) ===", code)
        try:
            ret, data = ctx.get_daily_short_volume(code)
            if ret != 0:
                logger.error("get_daily_short_volume failed: %s", data)
            elif data is not None and not data.empty:
                logger.info("Daily Short Volume DataFrame:\n%s", data.to_string())
            else:
                logger.info("No daily short volume data returned.")
        except Exception as e:
            logger.exception("get_daily_short_volume error: %s", e)

        # ── Top Ten Buy/Sell Brokers ────────────────────────────────────
        logger.info("\n=== get_top_ten_buy_sell_brokers(%s) ===", code)
        try:
            ret, data = ctx.get_top_ten_buy_sell_brokers(code)
            if ret != 0:
                logger.error("get_top_ten_buy_sell_brokers failed: %s", data)
            elif data is not None and not data.empty:
                logger.info("Top 10 Brokers DataFrame:\n%s", data.to_string())
            else:
                logger.info("No broker data returned.")
        except Exception as e:
            logger.exception("get_top_ten_buy_sell_brokers error: %s", e)

    finally:
        ctx.close()
        logger.info("Done.")
