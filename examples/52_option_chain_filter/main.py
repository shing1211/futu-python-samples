#!/usr/bin/env python3
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

    stock = "US.NVDA"

    # Get expiration dates first
    ret, expirations = ctx.get_option_expiration_date(stock)
    if ret != 0:
        print(f"get_option_expiration_date failed: {expirations}")
        ctx.close()
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
    print(f"  Filter: CALL options, ITM (moneyness 0.7-1.3), delta > 0.3\n")

    # Build a filter -- ITM calls with delta > 0.3
    filt = ft.OptionDataFilter()
    filt.filter_call_put = ft.OptionCondType.CALL
    filt.moneyness_min   = 0.7   # ITM
    filt.moneyness_max   = 1.3
    filt.delta_min       = 0.3   # delta > 0.3

    ret, chain = ctx.get_option_chain(stock, exp_date, ft.OptionType.CALL, filt)
    if ret != 0:
        print(f"  get_option_chain failed: {chain}")
    elif chain is None or (hasattr(chain, "empty") and chain.empty):
        print("  (no contracts match filter)")
    else:
        print(f"  Matched {len(chain)} contract(s).")
        show_cols = [c for c in ["code", "strike_price", "last_price",
                                  "implied_volatility", "delta", "open_interest"]
                     if c in chain.columns]
        print(chain[show_cols].head(10).to_string(index=False))

    ctx.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
