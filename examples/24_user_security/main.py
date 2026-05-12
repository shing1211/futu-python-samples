# -*- coding: utf-8 -*-
"""自选股分组管理 (get_user_security / modify_user_security)

Demonstrates:
  - get_user_security: list stocks in a watchlist group
  - modify_user_security: ADD/DEL stocks to/from a group
  - ModifyUserSecurityOp: ADD, DEL, SORT
  - All returned fields logged
"""
import logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("=== Watchlist (User Security) Group Demo ===")

    ctx = create_quote_context()

    try:
        group = "MyTechStocks"
        test_code = "HK.00700"

        # ── List group contents ────────────────────────────────────────
        logger.info("\n=== get_user_security: %s ===", group)
        ret, data = ctx.get_user_security(group)
        if ret != 0:
            logger.error("get_user_security failed: %s", data)
        else:
            if data.empty:
                logger.info("Group '%s' is empty", group)
            else:
                logger.info("Stocks in group (%d):", len(data))
                logger.info("Columns: %s", list(data.columns))
                for _, row in data.iterrows():
                    logger.info("  code=%s name=%s", row.get("code"), row.get("name"))
                logger.info("\n%s", data.to_string())

        # ── Add stock to group ──────────────────────────────────────────
        logger.info("\n=== modify_user_security: ADD %s to '%s' ===", test_code, group)
        ret, data = ctx.modify_user_security(
            group_name=group,
            op=ft.ModifyUserSecurityOp.ADD,
            code_list=[test_code],
        )
        logger.info("modify_user_security (ADD) ret=%d data=%s", ret, data)

        # ── List again after add ────────────────────────────────────────
        logger.info("\n=== get_user_security after ADD ===")
        ret, data = ctx.get_user_security(group)
        if ret == 0:
            logger.info("Stocks now in group: %d", len(data))
            for _, row in data.iterrows():
                logger.info("  code=%s name=%s", row.get("code"), row.get("name"))

        # ── Delete stock from group ─────────────────────────────────────
        logger.info("\n=== modify_user_security: DEL %s from '%s' ===", test_code, group)
        ret, data = ctx.modify_user_security(
            group_name=group,
            op=ft.ModifyUserSecurityOp.DEL,
            code_list=[test_code],
        )
        logger.info("modify_user_security (DEL) ret=%d data=%s", ret, data)

    finally:
        ctx.close()
        logger.info("Done.")