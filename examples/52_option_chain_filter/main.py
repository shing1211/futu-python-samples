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
52 — Option Chain with Data Filters

get_option_chain() returns all options for an underlying.
But raw chains can be huge -- hundreds of strikes across many expirations.
OptionDataFilter lets you slice the chain by delta, IV rank, volume,
open interest, and moneyness so you get only the contracts you care about.

This is how you build a real options screener -- filter first, then analyze.

SDK: OpenQuoteContext.get_option_chain() + OptionDataFilter
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import futu as ft
from connect import create_quote_context


def main():
    ctx = create_quote_context()
    try:
    
        stock = "US.NVDA"
    
        # Get expiration dates first
        ret, expirations = ctx.get_option_expiration_date(stock)
        if ret != 0:
            print(f"get_option_expiration_date failed: {expirations}")
            return
    
        # Columns: strike_time (date), option_expiry_date_distance (days), expiration_cycle (WEEK/MONTH/...)
        print(f"Underlying: {stock}")
        print(f"Nearest 3 expirations:")
        for _, row in expirations.head(3).iterrows():
            print(f"  {row['strike_time']} (in {row['option_expiry_date_distance']} days, {row['expiration_cycle']})")
        print()
    
        # Use the nearest expiration
        exp_row = expirations.iloc[0]
        exp_date = exp_row["strike_time"]
        cycle = exp_row["expiration_cycle"]
    
        print(f"=== Filtering {stock} {exp_date} ({cycle}) ===")
        print(f"  Filter: CALL options, delta > 0.3, moneyness 0.7-1.3 applied client-side\n")
    
        # Build a filter -- calls with delta > 0.3
        #
        # OptionDataFilter only defines the Greeks and volume/interest bounds;
        # it has no filter_call_put or moneyness_min/max. Call/put selection is
        # the option_type argument on get_option_chain, and moneyness has no
        # filter equivalent, so it is applied client-side after the fetch.
        filt = ft.OptionDataFilter(delta_min=0.3)
        MON_Y_MIN, MON_Y_MAX = 0.7, 1.3

        ret, chain = ctx.get_option_chain(
            stock, start=exp_date, end=exp_date,
            option_type=ft.OptionType.CALL,
            data_filter=filt,
        )
        if ret != 0:
            print(f"  get_option_chain failed: {chain}")
        elif chain is None or (hasattr(chain, "empty") and chain.empty):
            print("  (no contracts match filter)")
        else:
            if {"strike_price", "last_price"} <= set(chain.columns):
                chain = chain[
                    (chain["strike_price"] / chain["last_price"]).between(
                        MON_Y_MIN, MON_Y_MAX
                    )
                ]
            print(f"  Matched {len(chain)} contract(s).")
            show_cols = [c for c in ["code", "strike_price", "last_price",
                                      "implied_volatility", "delta", "open_interest"]
                         if c in chain.columns]
            print(chain[show_cols].head(10).to_string(index=False))
    
    finally:
        ctx.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
