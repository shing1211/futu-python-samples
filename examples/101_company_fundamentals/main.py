# -*- coding: utf-8 -*-
"""公司基本面 (get_company_profile / get_company_executives / get_company_executive_background / get_company_operational_efficiency)

Demonstrates:
  - get_company_profile: company profile data (name, value, field_type)
  - get_company_executives: executive info
  - get_company_executive_background: executive background
  - get_company_operational_efficiency: operational metrics
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
    logger.info("=== Company Fundamentals Demo ===")

    parser = argparse.ArgumentParser()
    parser.add_argument("--code", default="HK.00700", help="Stock code")
    args = parser.parse_args()

    code = args.code
    ctx = create_quote_context()

    try:
        # ── Company Profile ─────────────────────────────────────────────────
        logger.info("\n=== get_company_profile(%s) ===", code)
        try:
            ret, data = ctx.get_company_profile(code)
            if ret != 0:
                logger.error("get_company_profile failed: %s", data)
            elif data is not None and not data.empty:
                logger.info("Company Profile DataFrame:\n%s", data.to_string())
            else:
                logger.info("No company profile data returned.")
        except Exception as e:
            logger.exception("get_company_profile error: %s", e)

        # ── Company Executives ─────────────────────────────────────────────
        logger.info("\n=== get_company_executives(%s) ===", code)
        try:
            ret, data = ctx.get_company_executives(code)
            if ret != 0:
                logger.error("get_company_executives failed: %s", data)
            elif data is not None and not data.empty:
                logger.info("Executives DataFrame:\n%s", data.to_string())
            else:
                logger.info("No executive data returned.")
        except Exception as e:
            logger.exception("get_company_executives error: %s", e)

        # ── Executive Background ───────────────────────────────────────────
        logger.info("\n=== get_company_executive_background(%s) ===", code)
        try:
            ret, data = ctx.get_company_executive_background(code)
            if ret != 0:
                logger.error("get_company_executive_background failed: %s", data)
            elif data is not None and not data.empty:
                logger.info("Executive Background DataFrame:\n%s", data.to_string())
            else:
                logger.info("No executive background data returned.")
        except Exception as e:
            logger.exception("get_company_executive_background error: %s", e)

        # ── Operational Efficiency ─────────────────────────────────────────
        logger.info("\n=== get_company_operational_efficiency(%s) ===", code)
        try:
            ret, data = ctx.get_company_operational_efficiency(code)
            if ret != 0:
                logger.error("get_company_operational_efficiency failed: %s", data)
            elif data is not None and not data.empty:
                logger.info("Operational Efficiency DataFrame:\n%s", data.to_string())
            else:
                logger.info("No operational efficiency data returned.")
        except Exception as e:
            logger.exception("get_company_operational_efficiency error: %s", e)

    finally:
        ctx.close()
        logger.info("Done.")
