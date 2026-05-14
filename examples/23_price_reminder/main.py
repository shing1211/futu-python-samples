# -*- coding: utf-8 -*-
"""价格提醒 (set_price_reminder / get_price_reminder)

Demonstrates:
  - set_price_reminder: add/delete price alert conditions
  - get_price_reminder: list all active alerts for a stock
   - SetPriceReminderOp: ADD, DEL
  - PriceReminderType: PRICE_UP, PRICE_DOWN, etc.
  - PriceReminderFreq: ONCE, ALWAYS
  - All returned fields logged

Note: Alerts trigger via push notifications — no polling needed.
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
    logger.info("=== Price Reminder Demo ===")

    ctx = create_quote_context()

    try:
        code = "HK.00700"

        # ── Add price alert (above threshold) ───────────────────────────
        logger.info("\n=== set_price_reminder: ADD above_500 (PRICE_UP) ===")
        ret, data = ctx.set_price_reminder(
            code=code,
            op=ft.SetPriceReminderOp.ADD,
            key=0,
            reminder_type=ft.PriceReminderType.PRICE_UP,
            reminder_freq=ft.PriceReminderFreq.ONCE,
            value=500.0,
            note="TCEH above 500!",
        )
        logger.info("set_price_reminder (ADD) ret=%d data=%s", ret, data)

        # ── Add price alert (below threshold) ───────────────────────────
        logger.info("\n=== set_price_reminder: ADD below_300 (PRICE_DOWN) ===")
        ret2, data2 = ctx.set_price_reminder(
            code=code,
            op=ft.SetPriceReminderOp.ADD,
            key=0,
            reminder_type=ft.PriceReminderType.PRICE_DOWN,
            reminder_freq=ft.PriceReminderFreq.ONCE,
            value=300.0,
            note="TCEH below 300!",
        )
        logger.info("set_price_reminder (ADD) ret=%d data=%s", ret2, data2)

        # ── Query all active alerts ─────────────────────────────────────
        logger.info("\n=== get_price_reminder: %s ===", code)
        ret3, data3 = ctx.get_price_reminder(code=code)
        if ret3 != 0:
            logger.error("get_price_reminder failed: %s", data3)
        else:
            if data3.empty:
                logger.info("No active price reminders")
            else:
                logger.info("Active reminders (%d):", len(data3))
                logger.info("Columns: %s", list(data3.columns))
                for _, row in data3.iterrows():
                    logger.info("  key=%s type=%s freq=%s value=%.2f note=%s enable=%s",
                                row.get("key", "?"), row.get("reminder_type", "?"),
                                row.get("reminder_freq", "?"), row.get("value", 0),
                                row.get("note", ""), row.get("enable", "?"))
                logger.info("\n%s", data3.to_string())

        # ── Delete alerts (use the key/id from get_price_reminder) ──────
        logger.info("\n=== set_price_reminder: DEL above_500 ===")
        ret4, data4 = ctx.set_price_reminder(
            code=code,
            op=ft.SetPriceReminderOp.DEL,
            key=0,  # in practice, read key/id from get_price_reminder response
        )
        logger.info("set_price_reminder (DEL) ret=%d data=%s", ret4, data4)

        logger.info("\n=== set_price_reminder: DEL below_300 ===")
        ret5, data5 = ctx.set_price_reminder(
            code=code,
            op=ft.SetPriceReminderOp.DEL,
            key=0,
        )
        logger.info("set_price_reminder (DEL) ret=%d data=%s", ret5, data5)

    finally:
        ctx.close()
        logger.info("Done.")