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
53 — Option Expiration Cycle Analysis

get_option_expiration_date() returns all expiration dates for an underlying.
The DataFrame already includes an expiration_cycle column (WEEK / MONTH / QUARTER)
so you can group the full roll calendar at a glance.

Why it matters: different strategies suit different cycles.
Weeklys are cheap but decay fast. Quarterlies are liquid but expensive.
Knowing which cycle you're trading matters for both Greeks and cost.

SDK: OpenQuoteContext.get_option_expiration_date()
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import futu as ft
from connect import create_quote_context


def main():
    ctx = create_quote_context()
    try:
    
        stocks = ["US.NVDA", "US.SPY"]
    
        for stock in stocks:
            print(f"=== {stock} ===")
            ret, expirations = ctx.get_option_expiration_date(stock)
            if ret != 0:
                print(f"  get_option_expiration_date failed: {expirations}\n")
                continue
    
            # Columns: strike_time, option_expiry_date_distance, expiration_cycle
            print(f"  Total: {len(expirations)} expiration dates")
            print(f"  Columns: {list(expirations.columns)}")
    
            # Group by cycle
            groups = {}
            for _, row in expirations.iterrows():
                cycle = row["expiration_cycle"]
                groups.setdefault(cycle, []).append(row["strike_time"])
    
            for cycle, dates in sorted(groups.items()):
                print(f"  [{cycle}] ({len(dates)} dates): {', '.join(dates[:5])}{'...' if len(dates) > 5 else ''}")
    
            # Show days-to-expiry distribution
            dist = expirations["option_expiry_date_distance"].describe()
            print(f"  Days to expiry: min={dist['min']:.0f}, median={dist['50%']:.0f}, max={dist['max']:.0f}")
            print()
    
    finally:
        ctx.close()
    print("Done.")


if __name__ == "__main__":
    main()
