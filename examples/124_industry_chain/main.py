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

"""产业链探索 (Industry Chain Explorer)

Demonstrates:
  - get_industrial_chain_list:        browse industry chains by keyword & market
  - get_industrial_chain_detail:      nodes (upstream/downstream) within a chain
  - get_industrial_chain_by_plate:    find chains linked to a sector plate
  - get_industrial_plate_info:        sector plate summary
  - get_industrial_plate_stock:       stocks within a sector plate
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
    logger.info("=== Industry Chain Explorer (SDK 10.8.6808+) ===\n")

    ctx = create_quote_context()

    try:
        keywords = ["AI", "semi", "EV", "chip"]
        for kw in keywords:
            logger.info("── Search chain: keyword=%s ──", kw)

            ret, data, *_ = ctx.get_industrial_chain_list(
                ft.Market.US,
                keyword=kw,
                count=5,
            )
            if ret != ft.RET_OK:
                logger.warning("  get_industrial_chain_list failed: %s", data)
                continue
            # `if not data` raises on a DataFrame: its truth value is
            # ambiguous. Test for null and empty explicitly.
            if data is None or data.empty:
                logger.info("  No chains found\n")
                continue

            logger.info("  Found %d chains", len(data))
            # data is a DataFrame, so iterate rows rather than treating each
            # element as a mapping.
            for _, chain in data.head(3).iterrows():
                chain_id = chain.get("chain_id")
                chain_name = chain.get("name", "?")
                chain_type = chain.get("chain_type", "?")
                logger.info("    id=%-6s name=%-30s type=%s", chain_id, chain_name, chain_type)

                if chain_id:
                    ret_d, detail = ctx.get_industrial_chain_detail(chain_id)
                    if ret_d == ft.RET_OK and isinstance(detail, dict):
                        nodes = detail.get("node_list", [])
                        if nodes:
                            logger.info("      Nodes (%d):", len(nodes))
                            for node in nodes[:5]:
                                logger.info("        layer=%s name=%s", node.get("layer", "?"), node.get("name", ""))
                    print("")

        logger.info("── Industry Plate Info & Stocks ──")
        ret, plates, *_ = ctx.get_industrial_chain_list(ft.Market.HK, keyword="tech", count=3)
        if ret == ft.RET_OK and plates is not None and not plates.empty:
            for _, plate in plates.iterrows():
                plate_id = plate.get("chain_id")
                if plate_id:
                    ret_i, info = ctx.get_industrial_plate_info(plate_id)
                    if ret_i == ft.RET_OK and isinstance(info, dict):
                        logger.info("  Plate info: %s", (info.get("summary", "") or "")[:100])

                    ret_s, stocks, *_ = ctx.get_industrial_plate_stock(
                        plate_id=plate_id,
                        sort_field=ft.PlateStockSortField.CHANGE_RATE,
                        ascend=False,
                        count=5,
                    )
                    if ret_s == ft.RET_OK and stocks is not None and not stocks.empty:
                        logger.info("    Top 5 stocks in plate:")
                        for _, row in stocks.iterrows():
                            logger.info("      %-16s name=%-20s chg=%-8s vol=%-8s",
                                        row.get("code", "?"),
                                        row.get("name", "?"),
                                        row.get("change_rate", "?"),
                                        row.get("volume", "?"))
                    logger.info("")

    finally:
        ctx.close()
        logger.info("Done.")
