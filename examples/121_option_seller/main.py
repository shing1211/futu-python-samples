# -*- coding: utf-8 -*-

# Copyright (c) 2026 shing1211
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""期权卖方策略筛选 (get_option_seller_screener)

Demonstrates:
  - get_option_seller_screener: screen option seller strategies (cash-secured put, covered call, etc.)
  - SellerType: PUT_SELL, CALL_SELL
  - SellerIndicatorType filters: premium, annualized return, OTM probability, IV, volume
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
    logger.info("=== Option Seller Strategy Screener (SDK 10.8.6808+) ===\n")

    ctx = create_quote_context()

    try:
        for seller_type, label in [
            (ft.SellerType.CASH_SECURED_PUT, "Cash-Secured Put"),
            (ft.SellerType.COVERED_CALL, "Covered Call"),
        ]:
            logger.info("── SellerType=%s (%s) ──", seller_type, label)

            ret, data = ctx.get_option_seller_screener(
                ft.OptionMarket.US_SECURITY,
                seller_type,
                sort_type=ft.SellerSortType.PREMIUM,
                is_asc=False,
            )
            if ret != ft.RET_OK:
                logger.warning("  get_option_seller_screener failed: %s", data)
                continue
            if data is None or data.empty:
                logger.info("  No results\n")
                continue

            logger.info("  Top 5 seller strategies in US options:")
            for _, row in data.head(5).iterrows():
                logger.info("    %-20s premium=%-8s ann_ret=%-6s OTM_prob=%-6s IV=%-6s vol=%-8s",
                            row.get("owner", "?"),
                            row.get("premium", "?"),
                            row.get("annualized_return", "?"),
                            row.get("otm_probability", "?"),
                            row.get("iv", "?"),
                            row.get("volume", "?"))
            logger.info("")

        logger.info("── Filtered: premium > $1.00, annualized return > 10%%, OTM probability > 70%% ──")
        filters = [
            ft.SellerFilter(ft.SellerIndicatorType.PREMIUM, interval_min=1.0),
            ft.SellerFilter(ft.SellerIndicatorType.ANNUALIZED_RETURN, interval_min=10.0),
            ft.SellerFilter(ft.SellerIndicatorType.OTM_PROBABILITY, interval_min=70.0),
        ]
        ret, data = ctx.get_option_seller_screener(
            ft.OptionMarket.US_SECURITY,
            ft.SellerType.CASH_SECURED_PUT,
            sort_type=ft.SellerSortType.PREMIUM,
            is_asc=False,
            filter_list=filters,
        )
        if ret == ft.RET_OK and data is not None and not data.empty:
            logger.info("  %d filtered results:", len(data))
            for _, row in data.iterrows():
                logger.info("    %-20s premium=%-8s ann_ret=%-6s%% OTM_prob=%-6s%% iv=%-6s",
                            row.get("owner", "?"),
                            row.get("premium", "?"),
                            row.get("annualized_return", "?"),
                            row.get("otm_probability", "?"),
                            row.get("iv", "?"))
        else:
            logger.info("  (no filtered results)\n")

    finally:
        ctx.close()
        logger.info("Done.")
