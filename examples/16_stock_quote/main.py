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

"""实时报价 (get_stock_quote)

Demonstrates:
  - subscribe: subscribe to QUOTE subtype before fetching
  - get_stock_quote: fetch real-time quote fields for multiple stocks
  - All quote fields: last_price, open, high, low, volume, turnover, pe, etc.
  - Cross-market: HK, US, SH, SZ stocks
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
    logger.info("=== Real-time Stock Quote Demo ===")

    ctx = create_quote_context()

    try:
        codes = ["HK.00700", "HK.HSImain", "US.AAPL", "SH.600000", "SZ.000001"]

        ret, _ = ctx.subscribe(codes, [ft.SubType.QUOTE])
        logger.info("subscribe ret=%d codes=%s", ret, codes)

        # ── get_stock_quote ───────────────────────────────────────────────
        logger.info("\n=== get_stock_quote: %s ===", codes)
        ret, data = ctx.get_stock_quote(codes)
        if ret != 0:
            logger.error("get_stock_quote failed: %s", data)
        else:
            logger.info("Retrieved %d quotes | Columns: %s", len(data), list(data.columns))
            logger.info("\nAll available fields per stock:")
            for _, row in data.iterrows():
                logger.info("\n  === %s (%s) ===", row.get("code", "?"), row.get("name", "?"))
                for col in data.columns:
                    val = row[col]
                    if col in ["update_time", "create_time"]:
                        continue  # skip timestamps for brevity
                    logger.info("    %-20s = %s", col, val)

            logger.info("\nFull DataFrame:\n%s", data.to_string())

    finally:
        ctx.close()
        logger.info("Done.")