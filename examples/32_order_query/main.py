# -*- coding: utf-8 -*-
"""订单查询 / 改单 / 撤单 / 成交查询

Demonstrates:
  - order_list_query: live orders filtered by status
  - history_order_list_query: historical orders with date range
  - deal_list_query: today's executed trades
  - history_deal_list_query: historical executed trades
  - modify_order: change price/qty of a live order (demo only)
  - Proper logging of all returned fields
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
    logger.info("=== Order & Deal Query Demo ===")

    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)

    try:
        pwd = get_demo_trade_password()
        ret, data = trd_ctx.unlock_trade(pwd)
        if ret != ft.RET_OK:
            logger.error("unlock_trade failed: %s", data)
            raise SystemExit(1)
        logger.info("unlock_trade: OK")

        # ── Live Orders (SUBMITTED) ───────────────────────────────────
        logger.info("\n=== order_list_query: SUBMITTED ===")
        ret, data = trd_ctx.order_list_query(
            status_filter_list=[ft.OrderStatus.SUBMITTED],
        )
        if ret != ft.RET_OK:
            logger.error("order_list_query failed: %s", data)
        else:
            if data.empty:
                logger.info("No live submitted orders")
            else:
                logger.info("Live orders (%d rows):", len(data))
                logger.info("Columns: %s", list(data.columns))
                for col in data.columns:
                    logger.info("  %s: %s", col, data[col].tolist())
                logger.info("\n%s", data.to_string())

        # ── Historical Orders ─────────────────────────────────────────
        logger.info("\n=== history_order_list_query (FILLED_ALL, last 6 months) ===")
        ret, data = trd_ctx.history_order_list_query(
            status_filter_list=[ft.OrderStatus.FILLED_ALL],
            start="2025-11-01",
            end="2026-05-12",
        )
        if ret != ft.RET_OK:
            logger.error("history_order_list_query failed: %s", data)
        else:
            if data.empty:
                logger.info("No filled orders in range")
            else:
                logger.info("Historical orders (%d rows):", len(data))
                logger.info("Columns: %s", list(data.columns))
                for col in data.columns:
                    logger.info("  %s: %s", col, data[col].tolist())
                logger.info("\n%s", data.to_string())

        # ── Today's Deals ─────────────────────────────────────────────
        logger.info("\n=== deal_list_query ===")
        ret, data = trd_ctx.deal_list_query()
        if ret != ft.RET_OK:
            logger.error("deal_list_query failed: %s", data)
        else:
            if data.empty:
                logger.info("No deals today")
            else:
                logger.info("Today's deals (%d rows):", len(data))
                logger.info("Columns: %s", list(data.columns))
                for col in data.columns:
                    logger.info("  %s: %s", col, data[col].tolist())
                logger.info("\n%s", data.to_string())

        # ── Historical Deals ──────────────────────────────────────────
        logger.info("\n=== history_deal_list_query (last 6 months) ===")
        ret, data = trd_ctx.history_deal_list_query(
            start="2025-11-01",
            end="2026-05-12",
        )
        if ret != ft.RET_OK:
            logger.error("history_deal_list_query failed: %s", data)
        else:
            if data.empty:
                logger.info("No historical deals")
            else:
                logger.info("Historical deals (%d rows):", len(data))
                logger.info("Columns: %s", list(data.columns))
                for col in data.columns:
                    logger.info("  %s: %s", col, data[col].tolist())
                logger.info("\n%s", data.to_string())

        # ── Modify Order (demo - requires active order) ──────────────
        logger.info("\n=== modify_order (requires active order — skipping if none) ===")
        ret, live = trd_ctx.order_list_query(status_filter_list=[ft.OrderStatus.SUBMITTED])
        if ret == ft.RET_OK and not live.empty:
            order_id = live.iloc[0]["order_id"]
            new_price = float(live.iloc[0]["price"]) * 1.01  # adjust +1%
            new_qty = int(live.iloc[0]["qty"])
            logger.info("Modifying order_id=%s: price %.2f -> %.2f, qty %s",
                        order_id, float(live.iloc[0]["price"]), new_price, new_qty)
            ret2, data2 = trd_ctx.modify_order(
                modify_order_op=ft.ModifyOrderOp.MODIFY,
                order_id=order_id,
                qty=new_qty,
                price=new_price,
                trd_env=ft.TrdEnv.SIMULATE,
            )
            logger.info("modify_order result: ret=%s data=%s", ret2, data2)
        else:
            logger.info("No active submitted orders to modify — skipping")

    finally:
        trd_ctx.close()
        logger.info("Done.")