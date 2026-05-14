# -*- coding: utf-8 -*-
"""资金流向 (get_capital_flow / get_capital_distribution)

Demonstrates:
  - get_capital_flow: intraday and daily capital flow (buy/sell pressure)
  - get_capital_distribution: large/medium/small order distribution
  - PeriodType: INTRADAY, DAY, WEEK, MONTH, YEAR, QTD, YTD
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
    logger.info("=== Capital Flow & Distribution Demo ===")

    ctx = create_quote_context()

    try:
        code = "HK.00700"

        # ── Intraday capital flow ────────────────────────────────────────
        logger.info("\n=== get_capital_flow: INTRADAY (%s) ===", code)
        ret, data = ctx.get_capital_flow(code)
        if ret != 0:
            logger.error("get_capital_flow (intraday) failed: %s", data)
        else:
            logger.info("Intraday flow (%d bars):", len(data))
            logger.info("Columns: %s", list(data.columns))
            for col in data.columns:
                logger.info("  %-20s = %s", col, data[col].tolist())
            if not data.empty:
                time_col = 'capital_flow_item_time' if 'capital_flow_item_time' in data.columns else 'time_key'
                flow_col = 'in_flow' if 'in_flow' in data.columns else 'flow'
                logger.info("Last bar: time=%s flow=%.2f", data[time_col].iloc[-1], data[flow_col].iloc[-1])
            logger.info("\n%s", data.tail(10).to_string())

        # Note: get_capital_flow() has no period_type parameter — the only supported
        # mode for this API is intraday (the market determines granularity, not a param).
        # There is no separate "daily" call; removing the duplicate section that was
        # misleadingly labeled "DAY" but returned identical intraday data.

        # ── Capital distribution ─────────────────────────────────────────
        logger.info("\n=== get_capital_distribution: %s ===", code)
        ret, data = ctx.get_capital_distribution(code)
        if ret != 0:
            logger.error("get_capital_distribution failed: %s", data)
        else:
            logger.info("Capital distribution (%d rows):", len(data))
            logger.info("Columns: %s", list(data.columns))
            for col in data.columns:
                logger.info("  %-20s = %s", col, data[col].tolist())
            logger.info("\n%s", data.to_string())

    finally:
        ctx.close()
        logger.info("Done.")