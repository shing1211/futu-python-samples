#!/usr/bin/env python3

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

"""
116 — Option Combo Order

Place a multi-leg combo order using place_combo_order with margin impact
check via comboorder_tradinginfo_query. Demonstrates the new SDK 10.7.6708
combo order API. Requires OpenD 10.7.6708+.

SIMULATE account only — no real orders.

SDK (10.7.6708+): OpenSecTradeContext.place_combo_order()
                                .comboorder_tradinginfo_query()
                                .position_list_query()
                                .cancel_all_order()
                                .unlock_trade()
     OpenQuoteContext.get_option_chain()
                .get_option_expiration_date()
                .get_stock_quote()
"""

import sys
import time
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
import futu as ft
from connect import create_quote_context, create_trade_context, get_demo_trade_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

STOCK = "US.NVDA"
TRD_ENV = ft.TrdEnv.SIMULATE


def find_leg_codes(ctx, expiry):
    ret, chain = ctx.get_option_chain(
        STOCK, start=expiry, end=expiry, option_type=ft.OptionType.CALL,
    )
    if ret != 0 or chain is None or chain.empty:
        return None, None

    ret_q, quotes = ctx.get_stock_quote([STOCK])
    spot = 0.0
    if ret_q == ft.RET_OK and quotes is not None and not quotes.empty:
        spot = float(quotes.iloc[0].get("last_price", 0))

    if spot <= 0:
        return None, None

    strikes = sorted(
        (float(r.get("strike_price", 0)) for _, r in chain.iterrows()
         if float(r.get("strike_price", 0)) > 0)
    )
    if len(strikes) < 2:
        return None, None

    atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - spot))
    if atm_idx == 0 or atm_idx >= len(strikes) - 1:
        return None, None

    expiry_clean = expiry.replace("-", "")
    short_strike = strikes[atm_idx + 1]
    long_strike = strikes[atm_idx - 1]

    long_code = f"{STOCK}{expiry_clean}C{long_strike:.0f}"
    short_code = f"{STOCK}{expiry_clean}C{short_strike:.0f}"

    return long_code, short_code, long_strike, short_strike, spot


def main():
    print(f"  === Option Combo Order (SDK 10.7.6708+) ===\n")
    print(f"  SIMULATE account only — no real orders.\n")
    print(f"  Strategy: Vertical Call Spread via place_combo_order")
    print(f"  Stock: {STOCK}\n")

    quote_ctx = create_quote_context()
    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.ALL)

    try:
        ret_unlock, msg = trd_ctx.unlock_trade(get_demo_trade_password())
        if ret_unlock != ft.RET_OK:
            print(f"  unlock_trade failed: {msg}")
            return

        ret_e, expirations = quote_ctx.get_option_expiration_date(
            STOCK, ft.IndexOptionType.NORMAL,
        )
        if ret_e != 0:
            print(f"  get_option_expiration_date failed: {expirations}")
            return

        expiry = None
        if isinstance(expirations, list) and len(expirations) > 0:
            expiry = str(expirations[0])[:10]
        elif hasattr(expirations, "iloc") and len(expirations) > 0:
            expiry = str(expirations.iloc[0].get("strike_time", ""))[:10]

        if not expiry:
            print(f"  No expirations found")
            return

        result = find_leg_codes(quote_ctx, expiry)
        if result is None or result[0] is None:
            print(f"  Could not determine option legs near ATM")
            return

        long_code, short_code, long_strike, short_strike, spot = result
        print(f"  Spot: {spot:.2f} | Expiry: {expiry}")
        print(f"  Long leg:  {long_code} (BUY)")
        print(f"  Short leg: {short_code} (SELL)\n")

        leg1 = ft.ComboLeg()
        leg1.code = long_code
        leg1.trd_side = ft.TrdSide.BUY
        leg1.qty_ratio = 1.0

        leg2 = ft.ComboLeg()
        leg2.code = short_code
        leg2.trd_side = ft.TrdSide.SELL
        leg2.qty_ratio = -1.0

        combo_legs = [leg1, leg2]

        print(f"  Checking margin impact via comboorder_tradinginfo_query...")
        ret_m, margin_info = trd_ctx.comboorder_tradinginfo_query(
            combo_legs, price=1.0, qty=1, trd_env=TRD_ENV,
        )
        if ret_m == ft.RET_OK and margin_info is not None and not margin_info.empty:
            row = margin_info.iloc[0]
            for col in margin_info.columns:
                print(f"    {col}: {row[col]}")
        else:
            print(f"    comboorder_tradinginfo_query returned: ret={ret_m} {margin_info}")

        print(f"\n  Placing combo order (1 contract)...")
        ret_c, order_table = trd_ctx.place_combo_order(
            combo_legs, price=1.0, qty=1, trd_env=TRD_ENV,
        )
        if ret_c != ft.RET_OK:
            print(f"  place_combo_order failed: {order_table}")
            return

        print(f"\n  Combo order result:")
        if order_table is not None and not order_table.empty:
            row = order_table.iloc[0]
            for col in order_table.columns:
                val = row[col]
                if col == "combo_legs":
                    print(f"    {col}:")
                    for cl in val:
                        print(f"      {cl}")
                else:
                    print(f"    {col}: {val}")

            order_id = row.get("order_id", "N/A")
            print(f"\n  Monitoring order {order_id} for 15s...")
            for i in range(3):
                time.sleep(5)
                ret_o, orders = trd_ctx.order_list_query(trd_env=TRD_ENV)
                if ret_o == ft.RET_OK and orders is not None and not orders.empty:
                    matching = orders[orders.get("order_id") == order_id]
                    if not matching.empty:
                        status = matching.iloc[0].get("order_status", matching.iloc[0].get("status", "N/A"))
                        filled = matching.iloc[0].get("dealt_qty", 0)
                        print(f"    [{i*5+5}s] status={status}, filled={filled}")
        else:
            print(f"  No order data returned")

        print(f"\n  Position query (show_option_strategy_view=True):")
        ret_p, positions = trd_ctx.position_list_query(
            trd_env=TRD_ENV, show_option_strategy_view=True,
        )
        if ret_p == ft.RET_OK and positions is not None and not positions.empty:
            for col in positions.columns:
                if col in ("code", "qty", "strategy_type", "position_type", "combo_id", "position_id"):
                    print(f"    {col}: {positions.iloc[0].get(col, 'N/A')}")
        else:
            print(f"    No combo positions found (expected in SIMULATE)")

    finally:
        print(f"\n  Cleaning up...")
        trd_ctx.cancel_all_order(trd_env=TRD_ENV)
        quote_ctx.close()
        trd_ctx.close()
        print(f"  Done.")


if __name__ == "__main__":
    main()
