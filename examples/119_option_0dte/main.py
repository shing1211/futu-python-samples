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

"""末日期权筛选 (get_option_zero_dte_screener + get_option_zero_dte_contract)

Demonstrates:
  - get_option_zero_dte_screener: screen 0DTE option underlyings
  - get_option_zero_dte_contract: list option contracts for a given underlying+expiry
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
    logger.info("=== 0DTE Options Screener (SDK 10.8.6808+) ===\n")

    ctx = create_quote_context()

    try:
        markets = [ft.OptionMarket.US_SECURITY, ft.OptionMarket.HK_SECURITY]
        for mkt in markets:
            label = "US" if mkt == ft.OptionMarket.US_SECURITY else "HK"
            logger.info("── OptionMarket=%s ──", label)

            ret, data = ctx.get_option_zero_dte_screener(
                mkt,
                sort_type=ft.ZeroDteSortType.VOLUME,
                is_asc=False,
                count=5,
            )
            if ret != ft.RET_OK:
                logger.warning("  get_option_zero_dte_screener failed: %s", data)
                continue
            if data is None or data.empty:
                logger.info("  No 0DTE underlyings found\n")
                continue

            logger.info("  Top 5 0DTE underlyings by volume:")
            for _, row in data.iterrows():
                logger.info("    %-16s vol=%-8s IV=%-6s price=%-8s chain_info=%s",
                            row.get("owner", "?"),
                            row.get("volume", "?"),
                            row.get("iv", "?"),
                            row.get("price", "?"),
                            "yes" if row.get("chain_info") else "no")

            best = data.iloc[0]
            owner = best.get("owner", "")
            chain_info = best.get("chain_info")
            strike_ts = best.get("strike_date_timestamp", 0)
            if owner and chain_info and strike_ts:
                logger.info("\n  Contracts for %s:", owner)
                ret_c, contracts = ctx.get_option_zero_dte_contract(
                    owner, int(strike_ts), chain_info,
                    sort_type=ft.ZeroDteContractSortType.VOLUME,
                    is_asc=False,
                )
                if ret_c == ft.RET_OK and contracts is not None and not contracts.empty:
                    for _, c in contracts.head(10).iterrows():
                        logger.info("    %-20s type=%-6s vol=%-8s OI=%-8s IV=%-6s delta=%-6s",
                                    c.get("option", c.get("name", "?")),
                                    c.get("option_type", "?"),
                                    c.get("volume", "?"),
                                    c.get("open_interest", "?"),
                                    c.get("iv", "?"),
                                    c.get("delta", "?"))
                else:
                    logger.warning("  get_option_zero_dte_contract failed: %s", contracts)
            logger.info("")

        logger.info("\n── Filtered: volume>1000, IV>0.3 ──")
        filters = [
            ft.ZeroDteFilter(ft.ZeroDteIndicatorType.VOLUME, interval_min=1000),
            ft.ZeroDteFilter(ft.ZeroDteIndicatorType.IV, interval_min=0.3),
        ]
        ret, data = ctx.get_option_zero_dte_screener(
            ft.OptionMarket.US_SECURITY,
            sort_type=ft.ZeroDteSortType.VOLUME,
            is_asc=False,
            count=5,
            filter_list=filters,
        )
        if ret == ft.RET_OK and data is not None and not data.empty:
            logger.info("  Filtered results: %d", len(data))
            for _, row in data.iterrows():
                logger.info("    %-16s vol=%-8s IV=%-6s price=%-8s",
                            row.get("owner", "?"),
                            row.get("volume", "?"),
                            row.get("iv", "?"),
                            row.get("price", "?"))

    finally:
        ctx.close()
        logger.info("Done.")
