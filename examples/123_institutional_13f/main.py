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

"""机构持仓追踪 (13F-style institutional tracking)

Demonstrates:
  - get_institution_list:              top institutions by position value
  - get_institution_profile:           institution overview
  - get_institution_holding_list:      holdings (stocks) for a given institution
  - get_institution_holding_change:    changes in holdings over time
  - get_institution_distribution:      sector breakdown of institutional portfolio
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
    logger.info("=== Institutional 13F Tracker (SDK 10.8.6808+) ===\n")

    ctx = create_quote_context()

    try:
        logger.info("── Top Institutions by Position Value (US) ──")
        # get_institution_list returns (ret, frame, next_page, all_count) -- a 4-tuple.
        ret, data, next_page, all_count = ctx.get_institution_list(
            ft.Market.US,
            sort_field=ft.InstitutionListSortField.POSITION_VALUE,
            sort_dir=ft.RankSortDir.DESCENDING,
            count=10,
        )
        if ret == ft.RET_OK and data is not None and not data.empty:
            for _, row in data.iterrows():
                logger.info("  id=%-6s name=%-30s value=%-12s count=%-5s",
                            row.get("institution_id", "?"),
                            (row.get("institution_name", "") or "?")[:30],
                            row.get("position_value", "?"),
                            row.get("position_count", "?"))
        else:
            logger.warning("  get_institution_list: %s", data)

        logger.info("\n── Top Institutions (HK) ──")
        ret, data, next_page, all_count = ctx.get_institution_list(
            ft.Market.HK,
            sort_field=ft.InstitutionListSortField.POSITION_VALUE,
            sort_dir=ft.RankSortDir.DESCENDING,
            count=5,
        )
        if ret == ft.RET_OK and data is not None and not data.empty:
            for _, row in data.iterrows():
                logger.info("  id=%-6s name=%-30s value=%-12s",
                            row.get("institution_id", "?"),
                            (row.get("institution_name", "") or "?")[:30],
                            row.get("position_value", "?"))
        else:
            logger.warning("  (no HK data)\n")

        inst_id = None
        ret, data, next_page, all_count = ctx.get_institution_list(
            ft.Market.US,
            sort_field=ft.InstitutionListSortField.POSITION_VALUE,
            sort_dir=ft.RankSortDir.DESCENDING,
            count=1,
        )
        if ret == ft.RET_OK and data is not None and not data.empty:
            inst_id = data.iloc[0].get("institution_id")
            name = data.iloc[0].get("institution_name", "?")

        if inst_id:
            logger.info("\n── Profile: institution_id=%s (%s) ──", inst_id, name)
            ret, data = ctx.get_institution_profile(ft.Market.US, inst_id)
            if ret == ft.RET_OK and data is not None:
                logger.info("  summary=%s", (data.get("summary", "") or "")[:200])

            logger.info("\n── Top 10 Holdings ──")
            ret, data, next_page, all_count = ctx.get_institution_holding_list(
                ft.Market.US, inst_id,
                sort_field=ft.InstitutionHoldingListSortField.HOLDING_VALUE,
                sort_dir=ft.RankSortDir.DESCENDING,
                count=10,
            )
            if ret == ft.RET_OK and data is not None and not data.empty:
                for _, row in data.iterrows():
                    logger.info("    %-16s value=%-12s pct=%-6s%% chg=%-8s",
                                row.get("code", "?"),
                                row.get("holding_value", "?"),
                                row.get("holding_pct", "?"),
                                row.get("change_shares", "?"))

            logger.info("\n── Recent Position Changes (New Buys) ──")
            ret, data, next_page, all_count = ctx.get_institution_holding_change(
                ft.Market.US, inst_id,
                change_type=ft.InstitutionHoldingChangeType.NEW,
                sort_field=ft.InstitutionHoldingChangeSortField.CHANGE_SHARES,
                sort_dir=ft.RankSortDir.DESCENDING,
                count=10,
            )
            if ret == ft.RET_OK and data is not None and not data.empty:
                for _, row in data.iterrows():
                    logger.info("    %-16s shares=%-10s pct=%-6s%% date=%s",
                                row.get("code", "?"),
                                row.get("change_shares", "?"),
                                row.get("change_pct", "?"),
                                row.get("holding_date", "?"))

            logger.info("\n── Sector Distribution ──")
            ret, data = ctx.get_institution_distribution(ft.Market.US, inst_id)
            if ret == ft.RET_OK and data is not None and not data.empty:
                for _, row in data.iterrows():
                    logger.info("    %-25s value=%-12s pct=%-6s%%",
                                row.get("industry_name", row.get("plate_name", "?")),
                                row.get("position_value", "?"),
                                row.get("position_pct", "?"))
        else:
            logger.info("  (skipping detail — no institution data available)")

    finally:
        ctx.close()
        logger.info("Done.")
