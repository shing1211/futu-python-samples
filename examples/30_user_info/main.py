# -*- coding: utf-8 -*-
"""交易账户信息 (get_acc_list / get_user_info / get_security_firm)

Demonstrates:
  - get_acc_list: list all trading accounts linked to the user
  - get_user_info: user profile and account details (quote context)
  - get_security_firm: brokerage firm info (returns plain str, not DataFrame)
  - All returned fields logged
"""
import logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_trade_context, create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("=== Account & User Info Demo ===")

    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)
    quote_ctx = create_quote_context()

    try:
        # ── Account list ───────────────────────────────────────────────
        logger.info("\n=== get_acc_list ===")
        ret, data = trd_ctx.get_acc_list()
        if ret != 0:
            logger.error("get_acc_list failed: %s", data)
        else:
            logger.info("Accounts (%d):", len(data))
            logger.info("Columns: %s", list(data.columns))
            for _, row in data.iterrows():
                logger.info("  acc_id=%s acc_name=%s mkt=%s",
                            row.get("acc_id", "?"), row.get("acc_name", "?"),
                            row.get("trd_market", "?"))
            logger.info("\n%s", data.to_string())

        # ── Security firm (broker) ──────────────────────────────────────
        logger.info("\n=== get_security_firm (quote context) ===")
        firm = quote_ctx.get_security_firm()
        logger.info("Security firm: %s (type: %s)", firm, type(firm))

        # ── User info ───────────────────────────────────────────────────
        logger.info("\n=== get_user_info (quote context) ===")
        ret, data = quote_ctx.get_user_info()
        if ret != 0:
            logger.error("get_user_info failed: %s", data)
        else:
            logger.info("User info type: %s", type(data))
            if isinstance(data, dict):
                for k, v in data.items():
                    logger.info("  %-20s = %s", k, v)
            elif hasattr(data, 'to_string'):
                logger.info("\n%s", data.to_string())
            else:
                logger.info("Data: %s", data)

    finally:
        trd_ctx.close()
        quote_ctx.close()
        logger.info("Done.")