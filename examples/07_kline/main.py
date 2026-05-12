# -*- coding: utf-8 -*-
"""K线数据 (get_cur_kline / request_history_kline)

Demonstrates:
  - get_cur_kline: current K-line bars (last N bars)
  - request_history_kline: historical K-line with date range
  - KLType: K-line period variants (K_DAY, K_1M, K_5M, K_15M, K_30M, K_1H, K_4H, K_1W, K_1MIN, etc.)
  - AuType: price adjustment types (qfq, bfq, none)
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
    logger.info("=== K-line Data Demo ===")

    ctx = create_quote_context()

    try:
        code = "HK.00700"

        # ── Current K-line (get_cur_kline) ────────────────────────────
        logger.info("\n=== get_cur_kline: %s last 10 daily bars ===", code)
        for ktype_label, ktype in [
            ("K_DAY (daily)", ft.KLType.K_DAY),
            ("K_60M (hourly)", ft.KLType.K_60M),
            ("K_30M", ft.KLType.K_30M),
            ("K_5M", ft.KLType.K_5M),
        ]:
            ret, data = ctx.get_cur_kline(code, num=5, ktype=ktype, AuType=ft.AuType.QFQ)
            if ret != 0:
                logger.error("get_cur_kline (%s) failed: %s", ktype_label, data)
            else:
                logger.info("--- %s (ret=%d, %d rows) ---", ktype_label, ret, len(data))
                logger.info("Columns: %s", list(data.columns))
                for col in data.columns:
                    logger.info("  %-15s = %s", col, data[col].tolist())
                logger.info("\n%s", data.to_string())

        # ── Historical K-line (request_history_kline) ───────────────────
        logger.info("\n=== request_history_kline: %s last 30 days ===", code)
        ret, data = ctx.request_history_kline(
            code,
            start="2026-04-01",
            end="2026-05-12",
            ktype=ft.KLType.K_DAY,
            AuType=ft.AuType.QFQ,
        )
        if ret != 0:
            logger.error("request_history_kline failed: %s", data)
        else:
            logger.info("Retrieved %d bars | Columns: %s", len(data), list(data.columns))
            for col in data.columns:
                logger.info("  %-15s = %s", col, data[col].tolist())
            logger.info("\nLast 5 bars:\n%s", data.tail(5).to_string())

        # ── Different AuType ───────────────────────────────────────────
        logger.info("\n=== request_history_kline: AuType comparison (bfq vs qfq) ===")
        for au_label, au_type in [("bfq (no adjustment)", ft.AuType.BFQ), ("qfq (adjusted)", ft.AuType.QFQ)]:
            ret, data = ctx.request_history_kline(code, start="2026-04-01", end="2026-05-12",
                                                  ktype=ft.KLType.K_DAY, AuType=au_type)
            if ret == 0:
                logger.info("--- %s: last close=%.2f ---", au_label, data['close'].iloc[-1])
            else:
                logger.error("%s failed: %s", au_label, data)

    finally:
        ctx.close()
        logger.info("Done.")