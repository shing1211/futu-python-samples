# -*- coding: utf-8 -*-
"""买卖盘 (get_order_book)

Demonstrates:
  - subscribe: subscribe to ORDER_BOOK subtype
  - get_order_book: fetch N-level bid/ask depth
  - Order book structure: price, volume, order count per level
  - All returned fields logged

The order book shows the full depth of buy/sell orders at each price level.
This is useful for understanding liquidity and support/resistance levels.
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
    logger.info("=== Order Book (Depth) Demo ===")

    ctx = create_quote_context()

    try:
        code = "HK.00700"

        ret = ctx.subscribe(code, ft.SubType.ORDER_BOOK)
        logger.info("subscribe ret=%d code=%s", ret, code)

        # ── 10-level order book ─────────────────────────────────────────
        logger.info("\n=== get_order_book: %s (10 levels) ===", code)
        ret, data = ctx.get_order_book(code, num=10)
        if ret != 0:
            logger.error("get_order_book failed: %s", data)
        else:
            logger.info("Keys in response: %s", list(data.keys()))

            bid = data.get("Bid", [])
            ask = data.get("Ask", [])

            logger.info("\nBID (Buy orders) — %d levels:", len(bid))
            logger.info("  %-8s %-12s %-10s %-8s", "Level", "Price", "Volume", "Count")
            for i, (price, vol, count) in enumerate(bid):
                logger.info("  %-8d %-12.2f %-12.0f %-8d", i + 1, price, vol, count)

            logger.info("\nASK (Sell orders) — %d levels:", len(ask))
            logger.info("  %-8s %-12s %-10s %-8s", "Level", "Price", "Volume", "Count")
            for i, (price, vol, count) in enumerate(ask):
                logger.info("  %-8d %-12.2f %-12.0f %-8d", i + 1, price, vol, count)

            # Best bid / best ask spread
            if bid and ask:
                spread = ask[0][0] - bid[0][0]
                spread_pct = spread / bid[0][0] * 100
                logger.info("\nBest bid=%.2f Best ask=%.2f Spread=%.2f (%.2f%%)",
                            bid[0][0], ask[0][0], spread, spread_pct)

        # ── 50-level order book (full depth) ───────────────────────────
        logger.info("\n=== get_order_book: %s (50 levels) ===", code)
        ret, data = ctx.get_order_book(code, num=50)
        if ret != 0:
            logger.error("get_order_book (50) failed: %s", data)
        else:
            bid = data.get("Bid", [])
            ask = data.get("Ask", [])
            logger.info("BID levels: %d | ASK levels: %d", len(bid), len(ask))
            # Sum total volume at bid vs ask
            total_bid_vol = sum(v for _, v, _ in bid)
            total_ask_vol = sum(v for _, v, _ in ask)
            logger.info("Total bid volume: %.0f | Total ask volume: %.0f | Ratio: %.2f",
                        total_bid_vol, total_ask_vol,
                        total_bid_vol / total_ask_vol if total_ask_vol else float('inf'))

    finally:
        ctx.close()
        logger.info("Done.")