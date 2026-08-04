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

"""预测市场·事件合约探索 (Prediction Market · Event Contract Discovery)

Demonstrates the SDK 10.9.6908 event contract navigation flow:
  - get_event_contract_category:     top-level categories (SPORTS, ...)
  - filter_competition:              competition filter options per tag
  - get_event_contract_series_list:  Series under a category/tag
  - get_event_contract_event_list:   Events under a Series
  - get_event_contract:              Contracts under an Event
  - get_event_contract_milestone_list: milestones of a competition/event
  - get_event_contract_snapshot:     YES/NO live snapshot of a found contract

Event contracts are binary YES/NO prediction contracts on future events.
Contracts are ephemeral, so they are resolved at runtime via discovery.
Requires OpenD 10.9.6908+ and Prediction Market quote permission.
"""

import logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def warn_if_opend_too_old(ctx) -> bool:
    """Return True if the connected OpenD gateway is too old for event contracts."""
    ret, gs = ctx.get_global_state()
    if ret == ft.RET_OK and isinstance(gs, dict):
        ver = gs.get("server_ver", "0")
        logger.info("OpenD server version: %s", ver)
        if str(ver).isdigit() and int(ver) < 1009:
            logger.warning("  Event contract APIs require OpenD 10.9.6908+ — upgrade OpenD: "
                           "https://www.futunn.com/download/OpenAPI")
            return True
    return False


def first_col(row, col):
    v = row.get(col)
    return v[0] if isinstance(v, list) and v else (v or "")


if __name__ == "__main__":
    logger.info("=== Prediction Market · Event Contract Discovery (SDK 10.9.6908+) ===\n")

    ctx = create_quote_context()
    try:
        if warn_if_opend_too_old(ctx):
            sys.exit(0)

        # 1. Top-level categories
        ret, cats = ctx.get_event_contract_category()
        if ret != ft.RET_OK:
            logger.warning("get_event_contract_category failed: %s", cats)
        else:
            logger.info("── Categories (%d) ──", len(cats))
            for _, row in cats.head(6).iterrows():
                logger.info("  %-12s %-20s tags=%s",
                            row.get("category", "?"), row.get("category_name", "?"),
                            row.get("tags", []))
        print("")

        # 2. Competition filter options (Sports)
        ret, comp = ctx.filter_competition(category="SPORTS")
        if ret != ft.RET_OK:
            logger.warning("filter_competition failed: %s", comp)
        else:
            logger.info("── Competition filters (SPORTS) ──")
            for _, row in comp.head(6).iterrows():
                competitions = first_col(row, "competition")
                scopes = first_col(row, "scope")
                logger.info("  %-12s comp=%s scope=%s",
                            row.get("tag", "?"), competitions, scopes)
        print("")

        # 3. Series under the first available Sports tag
        tag = None
        if ret == ft.RET_OK and not comp.empty:
            tag = comp.iloc[0].get("tag")
        ret_s, series = ctx.get_event_contract_series_list(category="SPORTS", tag=tag)
        if ret_s != ft.RET_OK:
            logger.warning("get_event_contract_series_list failed: %s", series)
            sys.exit(0)
        logger.info("── Series under SPORTS/%s (%d) ──", tag or "all", len(series))
        for _, row in series.head(5).iterrows():
            logger.info("  %-16s %-40s freq=%s",
                        row.get("series_code", "?"), row.get("series_name", "?"),
                        row.get("frequency", "?"))
        print("")

        # 4. Events under the first Series
        series_code = series.iloc[0].get("series_code")
        ret_e, events, page = ctx.get_event_contract_event_list(series_code, count=5)
        if ret_e != ft.RET_OK:
            logger.warning("get_event_contract_event_list failed: %s", events)
            sys.exit(0)
        logger.info("── Events under %s (%d) page=%r ──", series_code, len(events), page)
        for _, row in events.head(5).iterrows():
            logger.info("  %-16s %-45s status=%s",
                        row.get("event_code", "?"), row.get("event_name", "?"),
                        row.get("status", "?"))
        print("")

        # 5. Contracts under the first Event
        event_code = events.iloc[0].get("event_code")
        ret_c, cont, page = ctx.get_event_contract(event_code, count=10)
        if ret_c != ft.RET_OK:
            logger.warning("get_event_contract failed: %s", cont)
            sys.exit(0)
        contracts = cont.get("contract_list")
        logger.info("── Contracts under %s (%d) page=%r ──", event_code, len(contracts), page)
        if contracts is not None and not contracts.empty:
            for _, row in contracts.head(8).iterrows():
                logger.info("  %-16s %-30s type=%s status=%s",
                            row.get("contract_code", "?"), row.get("title", "?"),
                            row.get("contract_type", "?"), row.get("status", "?"))
            print("")
            recs = cont.get("recommend_contracts") or []
            if recs:
                logger.info("  Recommended contracts: %s", recs[:5])
                print("")

            # 6. Milestones for the related event
            ret_m, miles, page = ctx.get_event_contract_milestone_list(
                category="SPORTS", related_event=event_code, count=5)
            if ret_m != ft.RET_OK:
                logger.info("  get_event_contract_milestone_list skipped: %s", miles)
            else:
                logger.info("── Milestones (related_event=%s) (%d) ──", event_code, len(miles))
                for _, row in miles.head(5).iterrows():
                    logger.info("  %-16s %-40s type=%s", row.get("milestone_code", "?"),
                                row.get("title", "?"), row.get("type", "?"))
            print("")

            # 7. Live snapshot of the first contract
            code = contracts.iloc[0].get("contract_code")
            ret_snap, snap = ctx.get_event_contract_snapshot([code])
            if ret_snap != ft.RET_OK:
                logger.warning("get_event_contract_snapshot failed: %s", snap)
            else:
                logger.info("── Snapshot: %s ──", code)
                row = snap.iloc[0]
                logger.info("  name=%-30s price=%-6s volume=%-8s status=%s",
                            row.get("name", "?"), row.get("price", "?"),
                            row.get("cumulative_volume", "?"), row.get("status", "?"))
                logger.info("  YES bid=%-6s sz=%s  ask=%-6s sz=%s",
                            row.get("yes_bid", "?"), row.get("yes_bid_size", "?"),
                            row.get("yes_ask", "?"), row.get("yes_ask_size", "?"))
                logger.info("  NO  bid=%-6s sz=%s  ask=%-6s sz=%s",
                            row.get("no_bid", "?"), row.get("no_bid_size", "?"),
                            row.get("no_ask", "?"), row.get("no_ask_size", "?"))
    finally:
        ctx.close()

    print("\nDone.")
