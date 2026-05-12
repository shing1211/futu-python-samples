# -*- coding: utf-8 -*-
"""资金流水 (get_acc_cash_flow)

Demonstrates:
  - get_acc_cash_flow: account cash flow history with direction filter
  - All cash flow directions: ALL, IN, OUT
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
    logger.info("=== Account Cash Flow Demo ===")

    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)

    try:
        pwd = get_demo_trade_password()
        ret, data = trd_ctx.unlock_trade(pwd)
        if ret != ft.RET_OK:
            logger.error("unlock_trade failed: %s", data)
            raise SystemExit(1)
        logger.info("unlock_trade: OK")

        for direction, label in [
            (ft.CashFlowDirection.ALL, "ALL"),
            (ft.CashFlowDirection.IN, "IN (deposits)"),
            (ft.CashFlowDirection.OUT, "OUT (withdrawals)"),
        ]:
            logger.info("\n=== get_acc_cash_flow: direction=%s (SIMULATE) ===", label)
            ret, data = trd_ctx.get_acc_cash_flow(
                clearing_date="",
                trd_env=ft.TrdEnv.SIMULATE,
                cashflow_direction=direction,
                start="2025-01-01",
                end="2026-05-12",
            )
            if ret != ft.RET_OK:
                logger.error("get_acc_cash_flow (%s) failed: %s", label, data)
            else:
                if data.empty:
                    logger.info("No cash flow records for direction=%s", label)
                else:
                    logger.info("Cash flow records (%d rows):", len(data))
                    logger.info("Columns: %s", list(data.columns))
                    for col in data.columns:
                        logger.info("  %-20s = %s", col, data[col].tolist())
                    logger.info("\n%s", data.to_string())

    finally:
        trd_ctx.close()
        logger.info("Done.")