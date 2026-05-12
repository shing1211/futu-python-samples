# -*- coding: utf-8 -*-
"""订单费用查询 (order_fee_query)

Demonstrates:
  - order_fee_query: fees for specific order IDs
  - First fetches historical orders, then queries fees
  - All returned fields logged
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
    logger.info("=== Order Fee Query Demo ===")

    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)

    try:
        pwd = get_demo_trade_password()
        ret, data = trd_ctx.unlock_trade(pwd)
        if ret != ft.RET_OK:
            logger.error("unlock_trade failed: %s", data)
            raise SystemExit(1)
        logger.info("unlock_trade: OK")

        # Find historical filled orders
        logger.info("\n=== Finding historical orders (FILLED_ALL) ===")
        ret, orders = trd_ctx.history_order_list_query(
            status_filter_list=[ft.OrderStatus.FILLED_ALL],
            start="2025-01-01",
            end="2026-05-12",
        )
        if ret != ft.RET_OK:
            logger.error("history_order_list_query failed: %s", orders)
        elif orders.empty:
            logger.info("No filled orders found in range")
        else:
            logger.info("Found %d filled orders", len(orders))
            logger.info("Columns: %s", list(orders.columns))
            # Log first 5 orders
            for i, row in orders.head(5).iterrows():
                logger.info(
                    "  order_id=%s code=%s side=%s qty=%s price=%s create_time=%s",
                    row.get("order_id"), row.get("code"), row.get("trd_side"),
                    row.get("qty"), row.get("price"), row.get("create_time"),
                )

            # Query fees for first few orders
            order_ids = orders.head(10)["order_id"].tolist()
            logger.info("\n=== order_fee_query: %d order IDs ===", len(order_ids))
            ret, fees = trd_ctx.order_fee_query(order_id_list=order_ids)
            if ret != ft.RET_OK:
                logger.error("order_fee_query failed: %s", fees)
            else:
                if fees.empty:
                    logger.info("No fee data returned")
                else:
                    logger.info("Fee data (%d rows):", len(fees))
                    logger.info("Columns: %s", list(fees.columns))
                    for col in fees.columns:
                        logger.info("  %-25s = %s", col, fees[col].tolist())
                    logger.info("\n%s", fees.to_string())

    finally:
        trd_ctx.close()
        logger.info("Done.")