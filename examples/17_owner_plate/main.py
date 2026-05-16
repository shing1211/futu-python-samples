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

"""所属板块 / 相关股票 (get_owner_plate / get_referencestock_list)

Demonstrates:
  - get_owner_plate: get industry/concept plates a stock belongs to
  - get_referencestock_list: warrant/bull-bear reference stocks
  - SecurityReferenceType: WARRANT, BULL_BEAR
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
    logger.info("=== Owner Plate & Reference Stock Demo ===")

    ctx = create_quote_context()

    try:
        code = "HK.00700"

        # ── get_owner_plate ─────────────────────────────────────────────
        logger.info("\n=== get_owner_plate: %s ===", code)
        ret, data = ctx.get_owner_plate([code])
        if ret != 0:
            logger.error("get_owner_plate failed: %s", data)
        else:
            logger.info("Plates (%d):", len(data))
            logger.info("Columns: %s", list(data.columns))
            for _, row in data.iterrows():
                logger.info("  code=%s name=%s plate_type=%s",
                            row.get("code"), row.get("name"),
                            row.get("plate_type", "?"))
            logger.info("\n%s", data.to_string())

        # ── get_referencestock_list: warrants ─────────────────────────────
        logger.info("\n=== get_referencestock_list: %s [WARRANT] ===", code)
        ret, data = ctx.get_referencestock_list(code, ft.SecurityReferenceType.WARRANT)
        if ret != 0:
            logger.error("get_referencestock_list (WARRANT) failed: %s", data)
        else:
            logger.info("Warrant reference stocks (%d):", len(data))
            if not data.empty:
                logger.info("Columns: %s", list(data.columns))
                for _, row in data.head(5).iterrows():
                    logger.info("  code=%s name=%s", row.get("code"), row.get("name"))
                logger.info("\n%s", data.head(5).to_string())

        # ── get_referencestock_list: bull/bear ────────────────────────────
        # Note: BULL_BEAR is not available in all SDK versions;
        # skip gracefully if the enum doesn't exist.
        try:
            ref_type_bull = ft.SecurityReferenceType.BULL_BEAR
        except AttributeError:
            logger.info("\n=== get_referencestock_list: %s [BULL_BEAR] — not available in this SDK ===", code)
        else:
            logger.info("\n=== get_referencestock_list: %s [BULL_BEAR] ===", code)
            ret, data = ctx.get_referencestock_list(code, ref_type_bull)
            if ret != 0:
                logger.error("get_referencestock_list (BULL_BEAR) failed: %s", data)
            else:
                logger.info("Bull/Bear reference stocks (%d):", len(data))
                if not data.empty:
                    logger.info("Columns: %s", list(data.columns))
                    for _, row in data.head(5).iterrows():
                        logger.info("  code=%s name=%s", row.get("code"), row.get("name"))
                    logger.info("\n%s", data.head(5).to_string())

    finally:
        ctx.close()
        logger.info("Done.")