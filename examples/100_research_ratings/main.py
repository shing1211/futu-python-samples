# -*- coding: utf-8 -*-
"""研究报告与评级 (get_research_analyst_consensus / get_research_rating_summary / get_research_morningstar_report)

Demonstrates:
  - get_research_analyst_consensus: average target price & analyst consensus
  - get_research_rating_summary: buy/hold/sell rating counts from analysts
  - get_research_morningstar_report: Morningstar analyst report metadata
"""
import logging
import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Research Ratings Demo")
    parser.add_argument("--code", default="HK.00700", help="Stock code")
    args = parser.parse_args()

    code = args.code
    logger.info("=== Research Ratings Demo: %s ===", code)

    ctx = create_quote_context()

    try:
        # ── get_research_analyst_consensus ────────────────────────────────
        logger.info("\n=== get_research_analyst_consensus ===")
        try:
            ret, df = ctx.get_research_analyst_consensus(code)
            if ret == ft.RetCode.SUCCESS and df is not None and not df.empty:
                logger.info("Retrieved %d rows | Columns: %s", len(df), list(df.columns))
                logger.info("\n%s", df.to_string())
            else:
                logger.warning("get_research_analyst_consensus ret=%d", ret)
        except Exception as e:
            logger.error("get_research_analyst_consensus error: %s", e)

        # ── get_research_rating_summary ────────────────────────────────────
        logger.info("\n=== get_research_rating_summary ===")
        try:
            ret, df = ctx.get_research_rating_summary(code)
            if ret == ft.RetCode.SUCCESS and df is not None and not df.empty:
                logger.info("Retrieved %d rows | Columns: %s", len(df), list(df.columns))
                logger.info("\n%s", df.to_string())
            else:
                logger.warning("get_research_rating_summary ret=%d", ret)
        except Exception as e:
            logger.error("get_research_rating_summary error: %s", e)

        # ── get_research_morningstar_report ────────────────────────────────
        logger.info("\n=== get_research_morningstar_report ===")
        try:
            ret, df = ctx.get_research_morningstar_report(code)
            if ret == ft.RetCode.SUCCESS and df is not None and not df.empty:
                logger.info("Retrieved %d rows | Columns: %s", len(df), list(df.columns))
                logger.info("\n%s", df.to_string())
            else:
                logger.warning("get_research_morningstar_report ret=%d", ret)
        except Exception as e:
            logger.error("get_research_morningstar_report error: %s", e)

    finally:
        ctx.close()
        logger.info("Done.")
