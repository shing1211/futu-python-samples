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

"""FedWatch利率监控 + 宏观经济指标 + 经济事件日历

Demonstrates:
  - get_fed_watch_target_rate:  Fed target rate probability distribution
  - get_fed_watch_dot_plot:     Fed dot plot (rate projections by FOMC members)
  - get_macro_indicator_list:   browse macro indicators by region
  - get_macro_indicator_history: fetch historical data for a macro indicator
  - get_economic_calendar:      upcoming economic events
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
    logger.info("=== FedWatch & Macro Monitor (SDK 10.8.6808+) ===\n")

    ctx = create_quote_context()

    try:
        logger.info("── FedWatch: Target Rate Probability ──")
        ret, data = ctx.get_fed_watch_target_rate()
        if ret == ft.RET_OK and data is not None and not data.empty:
            for _, row in data.iterrows():
                logger.info("  meeting=%-16s range=%-12s prob=%-6s%%",
                            row.get("meeting_date", "?"),
                            row.get("target_range", "?"),
                            row.get("probability", "?"))
        else:
            logger.warning("  get_fed_watch_target_rate: %s", data)

        logger.info("\n── FedWatch: Dot Plot ──")
        ret, data = ctx.get_fed_watch_dot_plot()
        if ret == ft.RET_OK and data is not None and not data.empty:
            for _, row in data.iterrows():
                logger.info("  year=%-4s rate=%-6s votes=%-3s median=%s",
                            row.get("year", "?"),
                            row.get("rate", "?"),
                            row.get("vote_count", "?"),
                            row.get("is_median", "?"))
        else:
            logger.warning("  get_fed_watch_dot_plot: %s", data)

        logger.info("\n── Macro Indicators (US) ──")
        ret, data = ctx.get_macro_indicator_list(ft.MacroRegion.US)
        if ret == ft.RET_OK and data is not None and not data.empty:
            logger.info("  Found %d macro indicators", len(data))
            for _, row in data.head(10).iterrows():
                logger.info("    id=%-5s name=%-30s unit=%-8s freq=%s",
                            row.get("indicator_id", "?"),
                            row.get("indicator_name", "?"),
                            row.get("data_unit", "?"),
                            row.get("frequency", "?"))
        else:
            logger.warning("  get_macro_indicator_list: %s", data)

        logger.info("\n── Macro Indicators (CN) ──")
        ret, data = ctx.get_macro_indicator_list(ft.MacroRegion.CN)
        if ret == ft.RET_OK and data is not None and not data.empty:
            logger.info("  Found %d macro indicators", len(data))
            for _, row in data.head(10).iterrows():
                logger.info("    id=%-5s name=%-30s unit=%-8s freq=%s",
                            row.get("indicator_id", "?"),
                            row.get("indicator_name", "?"),
                            row.get("data_unit", "?"),
                            row.get("frequency", "?"))

        logger.info("\n── Macro Indicator History (US, first indicator) ──")
        ret, data = ctx.get_macro_indicator_list(ft.MacroRegion.US)
        if ret == ft.RET_OK and data is not None and not data.empty:
            indicator_id = data.iloc[0].get("indicator_id")
            name = data.iloc[0].get("indicator_name", "?")
            ret, hist = ctx.get_macro_indicator_history(indicator_id, max_count=5)
            if ret == ft.RET_OK and hist is not None and not hist.empty:
                logger.info("  History for '%s' (id=%s):", name, indicator_id)
                for _, row in hist.iterrows():
                    logger.info("    time=%-12s value=%s", row.get("time", "?"), row.get("value", "?"))
            else:
                logger.info("  (no history)\n")

        logger.info("\n── Economic Calendar (US, this week) ──")
        import datetime
        today = datetime.date.today()
        end = today + datetime.timedelta(days=7)
        ret, data = ctx.get_economic_calendar(
            begin_date=today.isoformat(),
            end_date=end.isoformat(),
            market_list=[ft.Market.US],
            importance=ft.EconomicImportance.HIGH,
            count=10,
        )
        if ret == ft.RET_OK and data is not None and not data.empty:
            for _, row in data.iterrows():
                logger.info("  %-12s %-30s importance=%-6s prev=%-10s forecast=%-10s",
                            row.get("date", "?"),
                            (row.get("event", row.get("title", "")) or "")[:30],
                            row.get("importance", "?"),
                            row.get("previous", "?"),
                            row.get("forecast", "?"))
        else:
            logger.info("  (no calendar data)\n")

    finally:
        ctx.close()
        logger.info("Done.")
