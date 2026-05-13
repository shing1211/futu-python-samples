#!/usr/bin/env python3
"""
42 — Capital Distribution

Where does institutional money actually sit?

get_capital_distribution() breaks down capital inflows/outflows across four
institutional tiers — Super (top 20%), Big, Mid, Small — giving you a read on
whether smart money is accumulating or distributing.

Complements 19_capital_flow which shows the overall flow direction.
This shows WHERE the money is concentrated.

SDK: OpenQuoteContext.get_capital_distribution(code)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import futu as ft
from connect import create_quote_context


def fmt_inflow(val):
    """Format capital in millions with sign."""
    if val is None:
        return "N/A"
    return f"{val:+.2f}M"


def main():
    ctx = create_quote_context()

    # A basket of stocks across HK, US, and HK tech
    stocks = [
        ("HK.00700", "Tencent"),
        ("HK.09988", "Alibaba"),
        ("HK.03690", "Meituan"),
        ("US.AAPL", "Apple"),
        ("US.NVDA", "NVIDIA"),
    ]

    print(f"{'Code':<12} {'Super In':>10} {'Big In':>10} {'Mid In':>10} {'Small In':>10} "
          f"{'Super Out':>10} {'Big Out':>10} {'Update Time':>20}")
    print("-" * 108)

    for code, name in stocks:
        ret, data = ctx.get_capital_distribution(code)
        if ret != 0:
            print(f"{code:<12} ERROR: {data}")
            continue

        # Inflows (positive = money in)
        super_in  = data['capital_in_super'].iloc[0]
        big_in    = data['capital_in_big'].iloc[0]
        mid_in    = data['capital_in_mid'].iloc[0]
        small_in  = data['capital_in_small'].iloc[0]

        # Outflows
        super_out = data['capital_out_super'].iloc[0]
        big_out   = data['capital_out_big'].iloc[0]

        update_time = data['update_time'].iloc[0]

        print(f"{code:<12} {fmt_inflow(super_in):>10} {fmt_inflow(big_in):>10} "
              f"{fmt_inflow(mid_in):>10} {fmt_inflow(small_in):>10} "
              f"{fmt_inflow(super_out):>10} {fmt_inflow(big_out):>10} {str(update_time):>20}")

    ctx.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
