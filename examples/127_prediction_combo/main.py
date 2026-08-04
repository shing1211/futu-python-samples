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

"""预测市场·事件合约 Combo 组合 (Prediction Market · Event Contract Combo)

Demonstrates the SDK 10.9.6908 prediction combo (parlay) surface:
  - get_valid_combo_list:   combo-eligible events and their contracts
  - request_combo_quotes:   RFQ for a multi-leg combo (ComboLeg objects)
  - place_combo_order:      optional SIMULATE trade using the RFQ quote_id

Combos mix multiple prediction events into a single YES/NO trade.
Quote side runs unconditionally; the trade side is guarded because
prediction-market SIMULATE trading requires the relevant permission.

Requires OpenD 10.9.6908+ and Prediction Market quote permission.
"""

import logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context, create_trade_context, get_demo_trade_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

TRD_ENV = ft.TrdEnv.SIMULATE


def build_combo_legs(ctx):
    """Pick two combo-eligible events and build ComboLegs. Returns (legs, mvc) or (None, None)."""
    ret, data, mvc, page = ctx.get_valid_combo_list(category="SPORTS", count=10)
    if ret != ft.RET_OK:
        logger.warning("get_valid_combo_list failed: %s", data)
        return None, None
    if data is None or data.empty or mvc is None:
        logger.warning("No combo-eligible events found (mvc=%s)", mvc)
        return None, None

    logger.info("── Combo-eligible events (%d) page=%r ──", len(data), page)
    events = []
    for _, row in data.head(5).iterrows():
        contracts = row.get("combo_contracts") or []
        events.append((row.get("event_name", "?"), contracts))
        logger.info("  %-40s contracts=%s", row.get("event_name", "?"), contracts[:4])
    print("")

    leg1_contracts = events[0][1]
    leg2_contracts = events[1][1] if len(events) > 1 else []
    if not leg1_contracts or not leg2_contracts:
        logger.warning("Insufficient combo contracts to build a parlay")
        return None, None

    leg1 = ft.ComboLeg()
    leg1.code = leg1_contracts[0]
    leg1.trd_side = ft.TrdSide.BUY
    leg1.qty_ratio = 1.0
    leg1.pred_side = ft.PredSide.YES

    leg2 = ft.ComboLeg()
    leg2.code = leg2_contracts[0]
    leg2.trd_side = ft.TrdSide.BUY
    leg2.qty_ratio = 1.0
    leg2.pred_side = ft.PredSide.NO

    return [leg1, leg2], mvc


def run_trade_section(legs, quote_id, ask_price):
    """Attempt a SIMULATE combo order. Prediction SIMULATE may require permission."""
    logger.info("\n── Trade: place_combo_order (SIMULATE only) ──")
    try:
        trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.NONE)
    except Exception as e:  # noqa: BLE001
        logger.warning("  create_trade_context failed: %s", e)
        return

    try:
        ret, msg = trd_ctx.unlock_trade(get_demo_trade_password())
        if ret != ft.RET_OK:
            logger.warning("  unlock_trade failed (prediction combo trade needs permission): %s", msg)
            return

        ret_m, margin = trd_ctx.comboorder_tradinginfo_query(
            legs, price=ask_price, qty=1, trd_env=TRD_ENV,
        )
        if ret_m == ft.RET_OK and margin is not None and not margin.empty:
            logger.info("  Margin impact: %s", dict(margin.iloc[0]))
        else:
            logger.info("  comboorder_tradinginfo_query: ret=%s %s", ret_m, margin)

        ret_c, order = trd_ctx.place_combo_order(
            legs, price=ask_price, qty=1, trd_env=TRD_ENV,
            quote_id=quote_id,
        )
        if ret_c != ft.RET_OK:
            logger.warning("  place_combo_order failed (SIMULATE prediction trading "
                           "may be unsupported): %s", order)
            return

        logger.info("  Combo order placed:")
        if order is not None and not order.empty:
            row = order.iloc[0]
            logger.info("    order_id=%s status=%s price=%s qty=%s",
                        row.get("order_id", "?"), row.get("order_status", "?"),
                        row.get("price", "?"), row.get("qty", "?"))
            for cl in row.get("combo_legs") or []:
                logger.info("      leg: %s", cl)
    finally:
        trd_ctx.close()


if __name__ == "__main__":
    logger.info("=== Prediction Market · Event Contract Combo (SDK 10.9.6908+) ===\n")

    quote_ctx = create_quote_context()
    try:
        legs, mvc = build_combo_legs(quote_ctx)
        if legs is None:
            logger.warning("Cannot build a combo — check OpenD 10.9.6908+ and "
                           "Prediction Market quote permission.")
            sys.exit(0)

        for leg in legs:
            logger.info("Leg: code=%s side=%s qty_ratio=%s pred_side=%s",
                        leg.code, leg.trd_side, leg.qty_ratio, leg.pred_side)
        print("")

        # RFQ — request quotes for the parlay
        ret, rfq = quote_ctx.request_combo_quotes(legs, mvc)
        if ret != ft.RET_OK:
            logger.warning("request_combo_quotes failed: %s", rfq)
            sys.exit(0)

        logger.info("── Combo RFQ ──")
        logger.info("  bid=%s ask=%s quote_id=%s should_retry=%s",
                    rfq.get("bid_price"), rfq.get("ask_price"),
                    rfq.get("quote_id"), rfq.get("should_retry"))
        echo_legs = rfq.get("combo_leg_list") or []
        for leg in echo_legs:
            logger.info("  echo leg: %s", leg)
        print("")

        quote_id = rfq.get("quote_id")
        ask_price = rfq.get("ask_price")
        if not ask_price or ask_price <= 0:
            logger.warning("No valid ask price returned from RFQ — skipping trade section")
            sys.exit(0)

        run_trade_section(legs, quote_id, float(ask_price))
    finally:
        quote_ctx.close()

    print("\nDone.")
