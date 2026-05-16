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

"""窝轮/涡轮数据 (get_warrant)

Demonstrates:
  - get_warrant: list all warrants (structured products) for an underlying
  - Warrant data: strike, expiry, premium, effective leverage, etc.
  - All returned fields logged

Warrants (窝轮/涡轮) are derivative instruments issued by banks against stocks.
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
    logger.info("=== Warrant Data Demo ===")

    ctx = create_quote_context()

    try:
        for owner in ["HK.00700", "HK.HSImain"]:
            logger.info("\n=== get_warrant: owner=%s ===", owner)
            ret, warrant_data = ctx.get_warrant(stock_owner=owner)
            if ret != 0:
                logger.error("get_warrant failed: %s", warrant_data)
            else:
                # warrant_data is (DataFrame, has_more, total_count) — unwrap
                if isinstance(warrant_data, tuple):
                    warrants, has_more, total = warrant_data
                else:
                    warrants = warrant_data
                    has_more = None
                    total = None
                if warrants.empty:
                    logger.info("No warrants found for %s", owner)
                else:
                    logger.info("Total warrants: %d | has_more=%s | Columns: %s",
                                len(warrants), has_more, list(warrants.columns))
                    for col in warrants.columns:
                        vals = warrants[col].tolist()[:5]
                        logger.info("  %-25s = %s", col, vals)
                    logger.info("\nFirst 5 warrants:\n%s", warrants.head(5).to_string())

    finally:
        ctx.close()
        logger.info("Done.")