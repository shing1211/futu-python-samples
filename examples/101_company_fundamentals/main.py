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
    parser = argparse.ArgumentParser(description="Company Fundamentals Demo")
    parser.add_argument("--code", default="HK.00700", help="Stock code")
    args = parser.parse_args()

    code = args.code
    logger.info("=== Company Fundamentals Demo: %s ===", code)

    ctx = create_quote_context()

    try:
        logger.info("=== get_company_profile ===")
        try:
            show("get_company_profile", *ctx.get_company_profile(code))
        except Exception as e:
            logger.error("get_company_profile: %s", e)

        logger.info("=== get_company_executives ===")
        try:
            show("get_company_executives", *ctx.get_company_executives(code))
        except Exception as e:
            logger.error("get_company_executives: %s", e)

        logger.info("=== get_company_executive_background ===")
        try:
            show("get_company_executive_background", *ctx.get_company_executive_background(code))
        except Exception as e:
            logger.error("get_company_executive_background: %s", e)

        logger.info("=== get_company_operational_efficiency ===")
        try:
            show("get_company_operational_efficiency", *ctx.get_company_operational_efficiency(code))
        except Exception as e:
            logger.error("get_company_operational_efficiency: %s", e)

    finally:
        ctx.close()
        logger.info("Done.")
