#!/usr/bin/env python3
"""
51 — Account List

get_acc_list() returns all sub-accounts under your user -- every
trading account, margin account, and futures account you have access to.

For multi-account setups (e.g. a family account with separate
positions, or a firm with multiple traders), this is how you discover
which accounts exist and what type each one is.

Note: get_acc_list() is available on OpenSecTradeContext only,
not OpenQuoteContext.

SDK: OpenSecTradeContext.get_acc_list()
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import futu as ft
from connect import create_trade_context


def main():
    trd_ctx = create_trade_context()

    print("=== ACCOUNTS ===\n")
    ret, accounts = trd_ctx.get_acc_list()
    if ret != 0:
        print(f"get_acc_list failed: {accounts}")
        trd_ctx.close()
        return

    if accounts is None or (hasattr(accounts, "empty") and accounts.empty):
        print("No accounts returned.")
        trd_ctx.close()
        return

    print(f"Columns: {list(accounts.columns)}\n")
    print(accounts.to_string(index=False))

    print("\n=== ACCOUNT SUMMARY ===\n")
    for _, row in accounts.iterrows():
        acc_id   = row.get("acc_id", row.get("acc", "?"))
        acc_type = row.get("acc_type", row.get("type", "?"))
        acc_name = row.get("acc_name", row.get("name", ""))
        print(f"  Account {acc_id} | type={acc_type} | name={acc_name}")

    trd_ctx.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
