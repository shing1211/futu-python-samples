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
    parser = argparse.ArgumentParser(description="Shareholders & Insiders Demo")
    parser.add_argument("--code", default="US.NVDA", help="Stock code")
    args = parser.parse_args()

    code = args.code
    logger.info("=== Shareholders & Insiders Demo: %s ===", code)

    ctx = create_quote_context()

    api_calls = [
        ("get_shareholders_overview", lambda: ctx.get_shareholders_overview(code)),
        ("get_shareholders_holding_changes", lambda: ctx.get_shareholders_holding_changes(code)),
        ("get_shareholders_holder_detail", lambda: ctx.get_shareholders_holder_detail(code, 0)),
        ("get_shareholders_institutional", lambda: ctx.get_shareholders_institutional(code)),
        ("get_insider_holder_list", lambda: ctx.get_insider_holder_list(code)),
        ("get_insider_trade_list", lambda: ctx.get_insider_trade_list(code)),
    ]

    try:
        for name, func in api_calls:
            logger.info("=== %s ===", name)
            try:
                show(name, *func())
            except Exception as e:
                logger.error("%s: %s", name, e)
    finally:
        ctx.close()
        logger.info("Done.")
