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

"""相关股票列表 (get_referencestock_list)

Demonstrates:
  - get_referencestock_list: get related warrant/bull-bear reference stocks
  - SecurityReferenceType: WARRANT, BULL_BEAR (BULL_BEAR may not exist in all SDK versions)
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
    logger.info("=== Reference Stock List Demo ===")

    ctx = create_quote_context()

    try:
        # Note: BULL_BEAR may not exist in all SDK versions; detect gracefully.
        try:
            bull_bear_type = ft.SecurityReferenceType.BULL_BEAR
            has_bull_bear = True
        except AttributeError:
            bull_bear_type = None
            has_bull_bear = False
            logger.info("SecurityReferenceType.BULL_BEAR not available in this SDK version")

        for code in ["HK.00700", "US.AAPL"]:
            logger.info("\n=== Processing %s ===", code)

            # WARRANT
            logger.info("\n  --- get_referencestock_list: %s [WARRANT] ---", code)
            ret, data = ctx.get_referencestock_list(code, ft.SecurityReferenceType.WARRANT)
            if ret != 0:
                logger.error("get_referencestock_list failed: %s", data)
            else:
                if data.empty:
                    logger.info("  No reference stocks found for type=WARRANT")
                else:
                    logger.info("  Count: %d | Columns: %s", len(data), list(data.columns))
                    for _, row in data.iterrows():
                        logger.info("    code=%s name=%s stock_type=%s",
                                    row.get("code"), row.get("name"),
                                    row.get("stock_type", "?"))
                    logger.info("\n  %s", data.to_string())

            # BULL_BEAR (if available)
            if has_bull_bear:
                logger.info("\n  --- get_referencestock_list: %s [BULL_BEAR] ---", code)
                ret, data = ctx.get_referencestock_list(code, bull_bear_type)
                if ret != 0:
                    logger.error("get_referencestock_list failed: %s", data)
                else:
                    if data.empty:
                        logger.info("  No reference stocks found for type=BULL_BEAR")
                    else:
                        logger.info("  Count: %d | Columns: %s", len(data), list(data.columns))
                        for _, row in data.iterrows():
                            logger.info("    code=%s name=%s stock_type=%s",
                                        row.get("code"), row.get("name"),
                                        row.get("stock_type", "?"))
                        logger.info("\n  %s", data.to_string())

    finally:
        ctx.close()
        logger.info("Done.")
