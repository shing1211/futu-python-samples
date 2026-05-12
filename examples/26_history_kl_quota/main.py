# -*- coding: utf-8 -*-
"""K线配额查询 (get_history_kl_quota)

Demonstrates:
  - get_history_kl_quota: check API rate limits for historical K-line requests
  - get_detail=True: show per-day quota usage breakdown
  - All returned fields logged

Rate limits apply to historical K-line requests. Monitor quota to avoid hitting limits.
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
    logger.info("=== Historical K-line Quota Demo ===")

    ctx = create_quote_context()

    try:
        # ── Basic quota check ───────────────────────────────────────────
        logger.info("\n=== get_history_kl_quota (summary) ===")
        ret, data = ctx.get_history_kl_quota()
        if ret != 0:
            logger.error("get_history_kl_quota failed: %s", data)
        else:
            logger.info("Quota used: %s | Remaining: %s",
                        data.get('used_quota', 'N/A'), data.get('remain_quota', 'N/A'))
            logger.info("Full response: %s", data)

        # ── Detailed quota breakdown ───────────────────────────────────
        logger.info("\n=== get_history_kl_quota (detail=True) ===")
        ret, data = ctx.get_history_kl_quota(get_detail=True)
        if ret != 0:
            logger.error("get_history_kl_quota (detail) failed: %s", data)
        else:
            logger.info("Quota used: %s | Remaining: %s",
                        data.get('used_quota', 'N/A'), data.get('remain_quota', 'N/A'))
            detail = data.get('detail', 'N/A')
            if detail != 'N/A':
                logger.info("Detail type: %s", type(detail))
                if isinstance(detail, dict):
                    for k, v in detail.items():
                        logger.info("  %-20s = %s", k, v)
                elif hasattr(detail, 'to_string'):
                    logger.info("Detail:\n%s", detail.to_string())
                else:
                    logger.info("Detail: %s", detail)
            logger.info("Full response: %s", data)

    finally:
        ctx.close()
        logger.info("Done.")