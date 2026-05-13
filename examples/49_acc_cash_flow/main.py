#!/usr/bin/env python3
"""
49 — Account Cash Flow

get_acc_cash_flow() returns the account's cash movement history --
deposits, withdrawals, fees, corporate actions -- as trade history.

Note: This API is on OpenSecTradeContext, not OpenQuoteContext.
It may not be available for all account types (returns -1 "Unknown protocol id").

SDK: OpenSecTradeContext.get_acc_cash_flow()
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import futu as ft
from connect import create_trade_context, get_demo_trade_password


def main():
    trd_ctx = create_trade_context()
    trd_ctx.unlock_trade(get_demo_trade_password())

    print("Fetching account cash flow...\n")

    # clearing_date is the settlement date; empty = all
    # cashflow_direction: 'N/A', 'IN', 'OUT'
    # Try REAL first; if locked try SIMULATE
    for env in ["REAL", "SIMULATE"]:
        print(f"Trying trd_env={env}...")
        ret, data = trd_ctx.get_acc_cash_flow(
            clearing_date="",
            trd_env=env,
            start="",
            end="",
        )
        if ret == 0:
            print(f"  success with {env}!")
            break
        print(f"  {env} returned {ret}: {data}")
    if ret != 0:
        print(f"get_acc_cash_flow returned {ret}: {data}")
        print("(This API may not be available for your account type.)")
        trd_ctx.close()
        return

    if data is None or (hasattr(data, "empty") and data.empty):
        print("No cash flow records returned.")
        trd_ctx.close()
        return

    print(f"Columns: {list(data.columns)}\n")
    print(data.to_string(index=False))

    trd_ctx.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
