# -*- coding: utf-8 -*-
"""财务报表 (get_financials_statements / revenue_breakdown / earnings_price_move / earnings_price_history)

Demonstrates:
  - get_financials_statements: fetch annual financial reports with EPS, revenue, net income, ROE, PE
  - get_financials_revenue_breakdown: revenue by segment
  - get_financials_earnings_price_move: stock price change around earnings announcements
  - get_financials_earnings_price_history: historical earnings summary with price data
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
    parser = argparse.ArgumentParser(description="Financial Statements Demo")
    parser.add_argument("--code", default="HK.00700", help="Stock code")
    args = parser.parse_args()

    code = args.code
    logger.info("=== Financial Statements Demo: %s ===", code)

    ctx = create_quote_context()

    try:
        # ── get_financials_statements ──────────────────────────────────────
        logger.info("\n=== get_financials_statements (annual, last 4) ===")
        try:
            ret, df = ctx.get_financials_statements(code, "annual", 4)
            if ret == ft.RetCode.SUCCESS and df is not None and not df.empty:
                logger.info("Retrieved %d reports | Columns: %s", len(df), list(df.columns))
                logger.info("\n%s", df.to_string())
            else:
                logger.warning("get_financials_statements ret=%d", ret)
        except Exception as e:
            logger.error("get_financials_statements error: %s", e)

        # ── get_financials_revenue_breakdown ──────────────────────────────
        logger.info("\n=== get_financials_revenue_breakdown ===")
        try:
            ret, df = ctx.get_financials_revenue_breakdown(code)
            if ret == ft.RetCode.SUCCESS and df is not None and not df.empty:
                logger.info("Retrieved %d rows | Columns: %s", len(df), list(df.columns))
                logger.info("\n%s", df.to_string())
            else:
                logger.warning("get_financials_revenue_breakdown ret=%d", ret)
        except Exception as e:
            logger.error("get_financials_revenue_breakdown error: %s", e)

        # ── get_financials_earnings_price_move ─────────────────────────────
        logger.info("\n=== get_financials_earnings_price_move ===")
        try:
            ret, df = ctx.get_financials_earnings_price_move(code)
            if ret == ft.RetCode.SUCCESS and df is not None and not df.empty:
                logger.info("Retrieved %d rows | Columns: %s", len(df), list(df.columns))
                logger.info("\n%s", df.to_string())
            else:
                logger.warning("get_financials_earnings_price_move ret=%d", ret)
        except Exception as e:
            logger.error("get_financials_earnings_price_move error: %s", e)

        # ── get_financials_earnings_price_history ──────────────────────────
        logger.info("\n=== get_financials_earnings_price_history ===")
        try:
            ret, df = ctx.get_financials_earnings_price_history(code)
            if ret == ft.RetCode.SUCCESS and df is not None and not df.empty:
                logger.info("Retrieved %d rows | Columns: %s", len(df), list(df.columns))
                logger.info("\n%s", df.to_string())
            else:
                logger.warning("get_financials_earnings_price_history ret=%d", ret)
        except Exception as e:
            logger.error("get_financials_earnings_price_history error: %s", e)

    finally:
        ctx.close()
        logger.info("Done.")
