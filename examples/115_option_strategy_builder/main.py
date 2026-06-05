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
115 — Option Strategy Builder

Enumerate available option strategies for an underlying, analyze their P&L
profile (max profit, max loss, breakeven, probability of profit, greeks),
and display valid spreads. Requires SDK 10.7.6708+ and OpenD 10.7.6708+.

No order placement — pure strategy discovery and analysis.

SDK (10.7.6708+): OpenQuoteContext.get_option_strategy()
                                .get_option_strategy_analysis()
                                .get_option_strategy_spread()
                                .get_option_expiration_date()
"""

import sys
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

STOCK = "US.NVDA"


def check_opend_version(ctx):
    ret, state = ctx.get_global_state()
    if ret == ft.RET_OK and isinstance(state, dict):
        ver = state.get("server_ver", "0")
        if ver.isdigit() and int(ver) < 1007:
            print(f"  WARNING: OpenD version {ver} detected — get_option_strategy requires OpenD 10.7.6708+")
            print(f"  Upgrade: https://www.futunn.com/en/download/OpenAPI\n")
            return False
    return True


def main():
    print(f"  === Option Strategy Builder (SDK 10.7.6708+) ===\n")
    print(f"  Underlying: {STOCK}\n")

    ctx = create_quote_context()
    try:
        if not check_opend_version(ctx):
            print(f"  Cannot proceed — OpenD gateway too old.")
            return

        ret_e, expirations = ctx.get_option_expiration_date(STOCK, ft.IndexOptionType.NORMAL)
        if ret_e != 0:
            print(f"  get_option_expiration_date failed: {expirations}")
            return

        expiries = []
        if isinstance(expirations, list):
            expiries = [str(e)[:10] for e in expirations[:3]]
        elif hasattr(expirations, "iloc"):
            expiries = [str(r.get("strike_time", ""))[:10] for _, r in expirations.head(3).iterrows()]

        if not expiries:
            print(f"  No expirations found")
            return

        print(f"  Expirations: {', '.join(expiries)}\n")
        expiry = expiries[0]

        ret_q, quotes = ctx.get_stock_quote([STOCK])
        spot = 0.0
        if ret_q == ft.RET_OK and quotes is not None and not quotes.empty:
            spot = float(quotes.iloc[0].get("last_price", 0))
            print(f"  Spot: {spot:.2f}\n")

        strategy_types = [
            (ft.OptionStrategyType.SINGLE, "Single Option"),
            (ft.OptionStrategyType.COVERED, "Covered Call"),
            (ft.OptionStrategyType.SPREAD, "Vertical Spread"),
            (ft.OptionStrategyType.STRADDLE, "Straddle"),
            (ft.OptionStrategyType.STRANGLE, "Strangle"),
            (ft.OptionStrategyType.COLLAR, "Collar"),
            (ft.OptionStrategyType.BUTTERFLY, "Butterfly"),
            (ft.OptionStrategyType.CONDOR, "Condor"),
            (ft.OptionStrategyType.IRON_BUTTERFLY, "Iron Butterfly"),
            (ft.OptionStrategyType.IRON_CONDOR, "Iron Condor"),
            (ft.OptionStrategyType.CALENDAR_SPREAD, "Calendar Spread"),
            (ft.OptionStrategyType.DIAGONAL_SPREAD, "Diagonal Spread"),
            (ft.OptionStrategyType.CUSTOM, "Custom"),
        ]

        for strategy_type, label in strategy_types:
            ret_s, strategies = ctx.get_option_strategy(
                STOCK, strategy_type,
                expire_time=expiry,
                far_expire_time=expiries[1] if len(expiries) > 1 else None,
            )
            if ret_s != ft.RET_OK or strategies is None:
                if "disconnect" in str(strategies).lower() or "connid" in str(strategies).lower():
                    print(f"  ⚠ OpenD gateway does not support get_option_strategy (ProtoId 3256).")
                    print(f"    Upgrade OpenD to 10.7.6708+: https://www.futunn.com/en/download/OpenAPI")
                    break
                continue

            empty = (hasattr(strategies, 'empty') and strategies.empty) or \
                    (isinstance(strategies, list) and len(strategies) == 0)
            if empty:
                continue

            print(f"  ── {label} ──")
            if isinstance(strategies, list):
                for s in strategies[:3]:
                    code = s.get("code", "N/A")
                    name = s.get("name", "N/A")
                    opt_strategy = s.get("option_strategy", "N/A")
                    legs = s.get("legs", [])
                    print(f"    [{code}] {name} ({opt_strategy}) — {len(legs)} legs")
                    for leg in legs[:4]:
                        leg_code = getattr(leg, 'code', 'N/A')
                        leg_action = getattr(leg, 'action', 'N/A')
                        leg_qty = getattr(leg, 'quantity', 'N/A')
                        print(f"        {leg_action} {leg_qty}x {leg_code}")
            elif hasattr(strategies, 'iterrows'):
                for _, s in strategies.head(3).iterrows():
                    code = s.get("code", "N/A")
                    name = s.get("name", "N/A")
                    print(f"    [{code}] {name}")
            print()

        print(f"  ═══════════════════════════════════════════")
        print(f"  Strategy Analysis (Single Option, {expiry}):\n")
        ret_s2, strats = ctx.get_option_strategy(
            STOCK, ft.OptionStrategyType.SINGLE,
            expire_time=expiry,
        )
        if ret_s2 == ft.RET_OK and strats is not None:
            if isinstance(strats, list) and len(strats) > 0:
                single = strats[0]
                legs = single.get("legs", [])
                if legs:
                    ret_a, analysis = ctx.get_option_strategy_analysis(legs)
                    if ret_a == ft.RET_OK:
                        if isinstance(analysis, list) and len(analysis) > 0:
                            a = analysis[0]
                            for key in ("name", "option_strategy", "max_profit", "max_loss",
                                         "prob_of_profit", "breakeven_points", "delta", "theta",
                                         "bid1", "ask1"):
                                val = a.get(key, "N/A")
                                print(f"    {key}: {val}")

        print(f"\n  ═══════════════════════════════════════════")
        print(f"  Spread Analysis ({expiry}):\n")
        ret_s3, spreads = ctx.get_option_strategy_spread(
            STOCK, ft.OptionStrategyType.SPREAD,
            expire_time=expiry,
        )
        if ret_s3 == ft.RET_OK and spreads is not None:
            if isinstance(spreads, list):
                print(f"    {len(spreads)} spread(s) available")
                for sp in spreads[:5]:
                    print(f"      spread: {sp}")
            elif hasattr(spreads, 'iterrows'):
                print(f"    {len(spreads)} spread(s) available")
                for _, sp in spreads.head(5).iterrows():
                    print(f"      {dict(sp)}")

    finally:
        ctx.close()
        print(f"\n  Done.")


if __name__ == "__main__":
    main()
