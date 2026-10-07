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

"""财报期权筛选 (get_option_earnings_screener + get_option_event + get_option_underlying_overview)

Demonstrates:
  - get_option_earnings_screener: screen stocks with earnings events & active options
  - get_option_event:            list unusual option activity
  - get_option_underlying_overview: batch underlying overview (IV, HV, volume, OI)
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
    logger.info("=== Earnings Options Dashboard (SDK 10.8.6808+) ===\n")

    ctx = create_quote_context()

    try:
        logger.info("── Earnings Options Screener (US, Top 5 by Volume) ──")
        ret, data = ctx.get_option_earnings_screener(
            ft.OptionMarket.US_SECURITY,
            sort_type=ft.EarningsSortType.VOLUME,
            is_asc=False,
            count=5,
        )
        if ret != ft.RET_OK:
            logger.error("get_option_earnings_screener failed: %s", data)
        else:
            # The screener returns (ret, dict), not a DataFrame: rows live in
            # 'item_list', alongside 'next_page', 'update_timestamp', 'all_count'.
            payload = data if isinstance(data, dict) else {}
            frame = payload.get("item_list")
            logger.info("  next_page=%s all_count=%s updated=%s",
                        payload.get("next_page", "?"),
                        payload.get("all_count", "?"),
                        payload.get("update_timestamp", "?"))
            frame = frame if frame is not None else []
            logger.info("  %d results", len(frame))
            rows = frame.iterrows() if hasattr(frame, "iterrows") else enumerate(frame)
            for _, row in rows:
                logger.info("    %-16s vol=%-8s OI=%-8s IV=%-6s IV%%=%-6s exp=%s",
                            row.get("owner", "?"),
                            row.get("volume", "?"),
                            row.get("open_interest", "?"),
                            row.get("iv", "?"),
                            row.get("iv_rank", row.get("iv_percentile", "?")),
                            row.get("strike_date_time", row.get("strike_date_timestamp", "?")))
            if len(frame) == 0:
                logger.info("  (server returned empty)\n")

        codes = ["US.AAPL", "US.NVDA", "US.TSLA", "US.MSFT", "US.AMZN"]
        logger.info("\n── Option Underlying Overview (Top US tech) ──")
        ret, data = ctx.get_option_underlying_overview(codes, ft.IndexOptionType.NORMAL)
        if ret == ft.RET_OK and data is not None and not data.empty:
            for _, row in data.iterrows():
                logger.info("    %-16s spot=%-8s IV=%-6s HV=%-6s vol=%-8s OI=%-8s",
                            row.get("code", "?"),
                            row.get("price", row.get("last_price", "?")),
                            row.get("iv", "?"),
                            row.get("hv", "?"),
                            row.get("volume", "?"),
                            row.get("open_interest", "?"))
        else:
            logger.info("  (no overview data)\n")

        logger.info("\n── Unusual Option Activity (US, last 10) ──")
        ret, data = ctx.get_option_event(
            ft.OptionMarket.US_SECURITY,
            count=10,
        )
        # get_option_event returns (ret, dict): events are a frame under
        # 'event_list', alongside 'next_page' and 'all_count'.
        if isinstance(data, dict):
            logger.info("  next_page=%s all_count=%s",
                        data.get("next_page", "?"), data.get("all_count", "?"))
            data = data.get("event_list")
        if ret == ft.RET_OK and data is not None and not data.empty:
            logger.info("  %d events", len(data))
            for _, row in data.iterrows():
                logger.info("    %-16s strategy=%-12s sentiment=%-8s vol=%-8s OI=%-6s IV=%-6s",
                            row.get("owner", "?"),
                            row.get("strategy", "?"),
                            row.get("sentiment", "?"),
                            row.get("volume", "?"),
                            row.get("open_interest", "?"),
                            row.get("iv", "?"))
        else:
            logger.info("  (no unusual activity)\n")

        logger.info("\n── Unusual Option Activity with Filters (US, Put Sweep, >1000 vol) ──")
        filters = [
            ft.OptionEventFilter(ft.EventIndicatorType.STRATEGY, string_value_list=["SWEEP"]),
            ft.OptionEventFilter(ft.EventIndicatorType.SENTIMENT, string_value_list=["PUT"]),
            ft.OptionEventFilter(ft.EventIndicatorType.VOLUME, interval_min=1000),
        ]
        ret, data = ctx.get_option_event(
            ft.OptionMarket.US_SECURITY,
            count=5,
            filter_list=filters,
        )
        if isinstance(data, dict):
            data = data.get("event_list")
        if ret == ft.RET_OK and data is not None and not data.empty:
            for _, row in data.iterrows():
                logger.info("    %-16s time=%-12s vol=%-8s price=%-8s",
                            row.get("owner", "?"),
                            row.get("time", "?"),
                            row.get("volume", "?"),
                            row.get("price", "?"))
        else:
            logger.info("  (no filtered results)\n")

    finally:
        ctx.close()
        logger.info("Done.")
