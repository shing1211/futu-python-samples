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
    parser = argparse.ArgumentParser(description="Research Ratings Demo")
    parser.add_argument("--code", default="HK.00700", help="Stock code")
    args = parser.parse_args()

    code = args.code
    logger.info("=== Research Ratings Demo: %s ===", code)

    ctx = create_quote_context()

    try:
        logger.info("=== get_research_analyst_consensus ===")
        try:
            show("get_research_analyst_consensus", *ctx.get_research_analyst_consensus(code))
        except Exception as e:
            logger.error("get_research_analyst_consensus: %s", e)

        logger.info("=== get_research_rating_summary ===")
        try:
            show("get_research_rating_summary", *ctx.get_research_rating_summary(code))
        except Exception as e:
            logger.error("get_research_rating_summary: %s", e)

        logger.info("=== get_research_morningstar_report ===")
        try:
            show("get_research_morningstar_report", *ctx.get_research_morningstar_report(code))
        except Exception as e:
            logger.error("get_research_morningstar_report: %s", e)

    finally:
        ctx.close()
        logger.info("Done.")
