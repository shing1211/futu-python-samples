# -*- coding: utf-8 -*-
"""股票筛选功能 (get_stock_filter)

Demonstrates:
  - SimpleFilter: filter by simple numeric fields (price, volume, etc.)
  - FinancialFilter: filter by financial metrics (ratios, earnings, etc.)
  - get_stock_filter: combined stock screener
  - StockField: all available filter fields
  - FinancialQuarter: annual vs quarterly financial data
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


def main():
    logger.info("=== Stock Filter (Screener) Demo ===")

    ctx = create_quote_context()

    try:
        # ── Simple Filter: stocks with price between 2-1000 HKD ─────────
        logger.info("\n--- SimpleFilter: CUR_PRICE 2-1000 HKD ---")
        simple_filter = ft.SimpleFilter()
        simple_filter.filter_min = 2
        simple_filter.filter_max = 1000
        simple_filter.stock_field = ft.StockField.CUR_PRICE
        simple_filter.is_no_filter = False

        # ── Financial Filter: current ratio 0.5-50 ───────────────────────
        logger.info("--- FinancialFilter: CURRENT_RATIO 0.5-50 (ANNUAL) ---")
        financial_filter = ft.FinancialFilter()
        financial_filter.filter_min = 0.5
        financial_filter.filter_max = 50
        financial_filter.stock_field = ft.StockField.CURRENT_RATIO
        financial_filter.is_no_filter = False
        financial_filter.sort = ft.SortDir.ASCEND  # Only one sort direction allowed
        financial_filter.quarter = ft.FinancialQuarter.ANNUAL

        # ── Run screener for HK market ───────────────────────────────────
        logger.info("\n=== get_stock_filter: HK market (Simple + Financial) ===")
        ret, ls = ctx.get_stock_filter(
            market=ft.Market.HK,
            filter_list=[simple_filter, financial_filter],
        )
        if ret != ft.RET_OK:
            logger.error("get_stock_filter failed: %s", ls)
        else:
            last_page, all_count, ret_list = ls
            logger.info("Result: last_page=%s all_count=%d ret_list=%d",
                       last_page, all_count, len(ret_list))

            if not ret_list:
                logger.info("No stocks matched the filter criteria")
            else:
                logger.info("First few matches:")
                for item in ret_list[:5]:
                    logger.info("  code=%s name=%s cur_price=%s current_ratio=%s",
                                item.stock_code, item.stock_name,
                                item.cur_price, item.current_ratio)
                    logger.info("    (raw item dict: %s)", dict(item) if hasattr(item, '__dict__') else item)

                logger.info("\nTotal returned: %d stocks | Total count (all pages): %d",
                            len(ret_list), all_count)

        # ── Try different markets ───────────────────────────────────────
        for market, label in [(ft.Market.US, "US"), (ft.Market.SH, "SH"), (ft.Market.SZ, "SZ")]:
            logger.info("\n=== get_stock_filter: %s market (price only) ===", label)
            sf = ft.SimpleFilter()
            sf.filter_min = 1
            sf.filter_max = 10000
            sf.stock_field = ft.StockField.CUR_PRICE
            sf.is_no_filter = False

            ret, ls = ctx.get_stock_filter(market=market, filter_list=[sf])
            if ret != ft.RET_OK:
                logger.error("get_stock_filter (%s) failed: %s", label, ls)
            else:
                last_page, all_count, ret_list = ls
                logger.info("%s: %d matches (showing first 3)", label, len(ret_list))
                for item in ret_list[:3]:
                    logger.info("  code=%s name=%s cur_price=%s", item.stock_code, item.stock_name, item.cur_price)

    finally:
        ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()