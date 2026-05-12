# -*- coding: utf-8 -*-
"""市场快照 (get_market_snapshot) — 所有股票

Demonstrates:
  - get_stock_basicinfo: enumerate all stocks in a market by SecurityType
  - get_market_snapshot: fetch snapshot data for up to 200 stocks per call
  - SecurityType variants: STOCK, IDX, ETF, WARRANT, BOND, FUTURE, OPTION
  - Rate limiting: max 200 stocks per call, 3s sleep between batches
  - All returned fields logged
"""
import logging
import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def loop_get_mkt_snapshot(ctx, market):
    """Fetch and log market snapshot for all stocks in a market."""
    logger.info("\n=== Market: %s ===", market)

    stock_types = [
        ft.SecurityType.STOCK,
        ft.SecurityType.IDX,
        ft.SecurityType.ETF,
        ft.SecurityType.WARRANT,
        ft.SecurityType.BOND,
    ]

    stock_codes = []
    for sub_type in stock_types:
        ret, data = ctx.get_stock_basicinfo(market, sub_type)
        if ret != 0:
            logger.warning("get_stock_basicinfo market=%s sub_type=%s failed: %s",
                           market, sub_type, data)
            continue
        if data.empty:
            continue
        codes = data['code'].tolist()
        logger.info("  %s: %d stocks (%s)", sub_type, len(codes), data['name'].iloc[0] if 'name' in data.columns else "")
        stock_codes.extend(codes)

    if not stock_codes:
        logger.warning("No stocks found for market %s", market)
        return

    logger.info("Total stocks to snapshot: %d (batched in groups of 200)", len(stock_codes))

    all_dataframes = []
    for i in range(0, len(stock_codes), 200):
        batch = stock_codes[i:i + 200]
        logger.info("\n  Batch %d/%d: fetching %d stocks (indices %d-%d)...",
                    i // 200 + 1, (len(stock_codes) + 199) // 200,
                    len(batch), i, min(i + 199, len(stock_codes) - 1))

        ret, data = ctx.get_market_snapshot(batch)
        if ret != 0:
            logger.error("get_market_snapshot batch failed: %s", data)
            continue

        logger.info("  Received %d rows | Columns: %s", len(data), list(data.columns))
        # Log first row as sample
        if not data.empty:
            logger.info("  Sample row:")
            for col in data.columns:
                logger.info("    %-20s = %s", col, data[col].iloc[0])
        all_dataframes.append(data)

        if i + 200 < len(stock_codes):
            time.sleep(3)  # Rate limit: 3s between batches

    if all_dataframes:
        import pandas as pd
        combined = pd.concat(all_dataframes, ignore_index=True)
        logger.info("\nTotal snapshot records: %d | Sample:\n%s", len(combined), combined.head(3).to_string())


if __name__ == "__main__":
    logger.info("=== Market Snapshot Demo ===")

    ctx = create_quote_context()

    try:
        for market in [ft.Market.HK, ft.Market.US, ft.Market.SZ, ft.Market.SH]:
            loop_get_mkt_snapshot(ctx, market)
    finally:
        ctx.close()
        logger.info("Done.")