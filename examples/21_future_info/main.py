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

"""期货合约信息 (get_future_info)

Demonstrates:
  - get_future_info: fetch contract specifications for futures
  - Multi-future: HK.HSImain (HSI), US.NQmain (Nasdaq futures)
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
    logger.info("=== Future Info Demo ===")

    ctx = create_quote_context()

    try:
        codes = ["HK.HSImain", "US.NQmain"]

        logger.info("\n=== get_future_info: %s ===", codes)
        ret, data = ctx.get_future_info(codes)
        if ret != 0:
            logger.error("get_future_info failed: %s", data)
        else:
            logger.info("Retrieved %d futures | Columns: %s", len(data), list(data.columns))
            for _, row in data.iterrows():
                logger.info("\n  === %s (%s) ===", row.get("code", "?"), row.get("name", "?"))
                for col in data.columns:
                    logger.info("    %-25s = %s", col, row.get(col, "?"))
            logger.info("\nFull DataFrame:\n%s", data.to_string())

    finally:
        ctx.close()
        logger.info("Done.")