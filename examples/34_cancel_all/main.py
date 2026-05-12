# -*- coding: utf-8 -*-
"""取消所有订单 (cancel_all_order)

Demonstrates:
  - order_list_query: view current submitted orders before cancel
  - cancel_all_order: cancel all open orders (requires unlock)
  - Proper logging of all order fields
"""
import sys
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_trade_context, get_demo_trade_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("=== Cancel All Orders Demo ===")

    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)

    try:
        pwd = get_demo_trade_password()
        ret, data = trd_ctx.unlock_trade(pwd)
        if ret != ft.RET_OK:
            logger.error("unlock_trade failed: %s", data)
            raise SystemExit(1)
        logger.info("unlock_trade: OK")

        # ── View Submitted Orders ─────────────────────────────────────
        logger.info("\n=== Current SUBMITTED orders ===")
        ret, data = trd_ctx.order_list_query(
            status_filter_list=[ft.OrderStatus.SUBMITTED],
        )
        if ret != ft.RET_OK:
            logger.error("order_list_query failed: %s", data)
        else:
            if data.empty:
                logger.info("No submitted orders")
            else:
                logger.info("Submitted orders (%d rows):", len(data))
                logger.info("Columns: %s", list(data.columns))
                for _, row in data.iterrows():
                    logger.info(
                        "  order_id=%s code=%s side=%s qty=%s price=%s status=%s",
                        row.get("order_id"), row.get("code"), row.get("trd_side"),
                        row.get("qty"), row.get("price"), row.get("status"),
                    )
                logger.info("\n%s", data.to_string())

        # ── Cancel All ────────────────────────────────────────────────
        logger.info("\n=== cancel_all_order (SIMULATE) ===")
        ret, data = trd_ctx.cancel_all_order(trd_env=ft.TrdEnv.SIMULATE)
        logger.info("cancel_all_order result: ret=%s data=%s", ret, data)
        if ret != ft.RET_OK:
            logger.error("cancel_all_order failed: %s", data)
        else:
            logger.info("Successfully cancelled all submitted orders")
            # Log cancellation details if returned
            if isinstance(data, dict):
                for k, v in data.items():
                    logger.info("  %s: %s", k, v)

    finally:
        trd_ctx.close()
        logger.info("Done.")