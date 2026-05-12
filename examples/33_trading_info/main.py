# -*- coding: utf-8 -*-
"""账户最大可买可卖数量 (acctradinginfo_query)

Demonstrates:
  - acctradinginfo_query: max buy/sell qty and related fields
  - Both BUY and SELL sides
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
    logger.info("=== Account Trading Info Demo ===")

    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)

    try:
        pwd = get_demo_trade_password()
        ret, data = trd_ctx.unlock_trade(pwd)
        if ret != ft.RET_OK:
            logger.error("unlock_trade failed: %s", data)
            raise SystemExit(1)
        logger.info("unlock_trade: OK")

        code = "HK.00700"
        price = 400.0

        for side, side_label in [(ft.TrdSide.BUY, "BUY"), (ft.TrdSide.SELL, "SELL")]:
            logger.info("\n=== acctradinginfo_query: %s %s @ %.2f ===", code, side_label, price)
            ret, data = trd_ctx.acctradinginfo_query(
                order_type=ft.OrderType.NORMAL,
                code=code,
                price=price,
                trd_side=side,
                trd_env=ft.TrdEnv.SIMULATE,
            )
            if ret != ft.RET_OK:
                logger.error("acctradinginfo_query (%s) failed: %s", side_label, data)
            else:
                logger.info("Fields (%d rows):", len(data))
                for col in data.columns:
                    logger.info("  %-20s = %s", col, data[col].values[0])
                logger.info("\nFull DataFrame:\n%s", data.to_string())

    finally:
        trd_ctx.close()
        logger.info("Done.")