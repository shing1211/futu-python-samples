# -*- coding: utf-8 -*-
"""股东与内部人 (shareholders + insiders)

Demonstrates:
  - get_shareholders_overview: shareholder overview
  - get_shareholders_holding_changes: holding change data
  - get_shareholders_holder_detail: holder detail (holder_type=0 for all)
  - get_shareholders_institutional: institutional holders
  - get_insider_holder_list: insider holder list
  - get_insider_trade_list: insider trade list
  - Each API call wrapped in try/except for resilience
  - Iterating through a list of (name, api_func, params) tuples
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
    logger.info("=== Shareholders & Insiders Demo ===")

    parser = argparse.ArgumentParser()
    parser.add_argument("--code", default="US.NVDA", help="Stock code")
    args = parser.parse_args()

    code = args.code
    ctx = create_quote_context()

    api_calls = [
        ("get_shareholders_overview", lambda: ctx.get_shareholders_overview(code), [code]),
        ("get_shareholders_holding_changes", lambda: ctx.get_shareholders_holding_changes(code), [code]),
        ("get_shareholders_holder_detail", lambda: ctx.get_shareholders_holder_detail(code, 0), [code]),
        ("get_shareholders_institutional", lambda: ctx.get_shareholders_institutional(code), [code]),
        ("get_insider_holder_list", lambda: ctx.get_insider_holder_list(code), [code]),
        ("get_insider_trade_list", lambda: ctx.get_insider_trade_list(code), [code]),
    ]

    try:
        for name, func, params in api_calls:
            logger.info("\n=== %s(%s) ===", name, code)
            try:
                ret, data = func()
                if ret != 0:
                    logger.error("%s failed: %s", name, data)
                elif data is not None and not data.empty:
                    logger.info("%s DataFrame:\n%s", name, data.to_string())
                else:
                    logger.info("No %s data returned.", name)
            except Exception as e:
                logger.exception("%s error: %s", name, e)

    finally:
        ctx.close()
        logger.info("Done.")
