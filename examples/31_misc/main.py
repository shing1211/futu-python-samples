# -*- coding: utf-8 -*-
"""杂项数据: 持仓变动 / 复权数据 / 用户分组 (get_holding_change_list / get_rehab / get_user_security_group)

Demonstrates:
  - get_holding_change_list: top holders' position changes (executives, funds)
  - get_rehab: dividend/split adjustment records (复权数据)
  - get_user_security_group: list all watchlist groups
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
    logger.info("=== Misc Data Demo (Holding Changes / Rehab / Groups) ===")

    ctx = create_quote_context()

    try:
        code = "HK.00700"

        # ── Holding changes (top holders position deltas) ─────────────────
        logger.info("\n=== get_holding_change_list: %s (2025) ===", code)
        for holder_type, type_label in [
            (ft.StockHolder.EXECUTIVE, "EXECUTIVE"),
            (ft.StockHolder.FUND, "FUND"),
        ]:
            logger.info("\n  --- holder_type=%s ---", type_label)
            ret, data = ctx.get_holding_change_list(
                code,
                holder_type=holder_type,
                start="2025-01-01",
                end="2026-05-12",
            )
            if ret != 0:
                logger.error("get_holding_change_list failed: %s", data)
            else:
                if data.empty:
                    logger.info("  No holding change records for type=%s", type_label)
                else:
                    logger.info("  Records: %d | Columns: %s", len(data), list(data.columns))
                    for col in data.columns:
                        logger.info("    %-20s = %s", col, data[col].tolist())
                    logger.info("\n  %s", data.head(5).to_string())

        # ── Rehab data (dividend/split adjustments) ────────────────────
        logger.info("\n=== get_rehab: %s ===", code)
        ret, data = ctx.get_rehab(code)
        if ret != 0:
            logger.error("get_rehab failed: %s", data)
        else:
            if data.empty:
                logger.info("No rehab records for %s", code)
            else:
                logger.info("Rehab records (%d):", len(data))
                logger.info("Columns: %s", list(data.columns))
                for col in data.columns:
                    logger.info("  %-20s = %s", col, data[col].tolist())
                logger.info("\n%s", data.to_string())

        # ── User security groups (all watchlists) ────────────────────────
        logger.info("\n=== get_user_security_group ===")
        ret, data = ctx.get_user_security_group()
        if ret != 0:
            logger.error("get_user_security_group failed: %s", data)
        else:
            if data.empty:
                logger.info("No watchlist groups found")
            else:
                logger.info("Groups (%d):", len(data))
                logger.info("Columns: %s", list(data.columns))
                for _, row in data.iterrows():
                    logger.info("  group_name=%s count=%s",
                                row.get("group_name", "?"), row.get("stock_count", "?"))
                logger.info("\n%s", data.to_string())

    finally:
        ctx.close()
        logger.info("Done.")