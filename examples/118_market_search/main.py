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

"""行情与资讯搜索 (get_search_quote + get_search_news)

Demonstrates:
  - get_search_quote: keyword search for market instruments
  - get_search_news:  keyword search for news, announcements, ratings
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
    logger.info("=== Market & News Search (SDK 10.8.6808+) ===\n")

    ctx = create_quote_context()

    try:
        keywords = ["NVDA", "AAPL", "00700"]
        for kw in keywords:
            logger.info("── search: keyword=%s ──", kw)

            ret, data = ctx.get_search_quote(kw, max_count=5)
            if ret != ft.RET_OK:
                logger.warning("  get_search_quote failed: %s", data)
            elif data is not None and not data.empty:
                logger.info("  Quotes: %d results", len(data))
                for _, row in data.head(5).iterrows():
                    logger.info("    code=%-16s name=%-20s market=%s type=%s",
                                row.get("code", "?"), row.get("stock_name", row.get("name", "?")),
                                row.get("market", "?"), row.get("security_type", "?"))
            else:
                logger.info("  Quotes: no results")

            ret, data = ctx.get_search_news(kw, max_count=3)
            if ret != ft.RET_OK:
                logger.warning("  get_search_news failed: %s", data)
            elif data is not None and not data.empty:
                logger.info("  News: %d results", len(data))
                for _, row in data.head(3).iterrows():
                    logger.info("    title=%-40s type=%-8s time=%s",
                                (row.get("title", "?") or "?")[:40],
                                row.get("news_sub_type", "?"),
                                row.get("time", row.get("timestamp", "?")))
            else:
                logger.info("  News: no results")

            logger.info("")

        ret, data = ctx.get_search_news("AAPL", max_count=5, news_sub_type=ft.NewsSubType.RATING)
        if ret == ft.RET_OK and data is not None and not data.empty:
            logger.info("── Analyst Ratings for AAPL ──")
            for _, row in data.iterrows():
                logger.info("  %s | %s", row.get("time", "?"),
                            (row.get("title", "") or "")[:60])
        else:
            logger.info("No analyst ratings found for AAPL\n")

        ret, data = ctx.get_search_quote("大 A 人工智能 ETF", max_count=5)
        if ret == ft.RET_OK and data is not None and not data.empty:
            logger.info("── Chinese keyword search ──")
            for _, row in data.iterrows():
                logger.info("  code=%-16s name=%-20s market=%s",
                            row.get("code", "?"), row.get("stock_name", row.get("name", "?")),
                            row.get("market", "?"))
        else:
            logger.info("No Chinese keyword results\n")

    finally:
        ctx.close()
        logger.info("Done.")
