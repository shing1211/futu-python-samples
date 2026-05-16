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

"""复权数据 (get_rehab — 除权除息记录)

Demonstrates:
  - get_rehab: dividend, split, and other corporate action adjustment records
  - Used for adjusting historical prices (forward/backward adjust)
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
    logger.info("=== Rehab (Corporate Actions) Demo ===")

    ctx = create_quote_context()

    try:
        for code in ["HK.00700", "US.AAPL"]:
            logger.info("\n=== get_rehab: %s ===", code)
            ret, data = ctx.get_rehab(code)
            if ret != 0:
                logger.error("get_rehab failed: %s", data)
            else:
                if data.empty:
                    logger.info("No rehab records for %s", code)
                else:
                    logger.info("Rehab records (%d):", len(data))
                    logger.info("Columns: %s", list(data.columns))
                    for col in data.columns:
                        logger.info("  %-20s = %s", col, data[col].tolist())
                    logger.info("\n%s", data.to_string())

    finally:
        ctx.close()
        logger.info("Done.")