#!/usr/bin/env python3
"""
45 — Broker Queue

get_broker_queue() shows who sits on the bid and ask — each broker's
queue position at each price level. This is the raw market structure signal:
before it gets aggregated into the order book, before it becomes trade prints.

Note: the BROKER push subtype (BrokerHandlerBase) requires LV1 data permission.
This example demonstrates the polling API get_broker_queue() which works
with standard accounts, and shows the push handler pattern for when
LV1 permission is available.

SDK: OpenQuoteContext.get_broker_queue()
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import futu as ft
from connect import create_quote_context


def print_broker_queue(data, side_label):
    """Print bid or ask side of the broker queue."""
    if data is None or (hasattr(data, "empty") and data.empty):
        print(f"  {side_label}: empty")
        return

    print(f"  {side_label} ({len(data)} levels):")
    print(f"  {'Broker ID':>10} {'Price':>12} {'Queue Pos':>10} {'Vol':>12}")
    print(f"  {'-'*10} {'-'*12} {'-'*10} {'-'*12}")
    for _, row in data.iterrows():
        # Columns vary by market; fall back to positional access
        if "broker_id" in row:
            bid = row["broker_id"]
            price = row.get("price", row.iloc[1])
            queue_pos = row.get("queue_pos", row.iloc[2])
            vol = row.get("vol", row.iloc[3])
        else:
            bid = row.iloc[0]
            price = row.iloc[1]
            queue_pos = row.iloc[2]
            vol = row.iloc[3]
        print(f"  {str(bid):>10} {float(price):>12.4f} {int(queue_pos):>10} {int(vol):>12,}")


def main():
    ctx = create_quote_context()

    stocks = ["HK.00700", "HK.09988"]

    for stock in stocks:
        print(f"=== {stock} ===")
        ret, data = ctx.get_broker_queue(stock)
        if ret != 0:
            print(f"  get_broker_queue returned {ret}: {data}")
            print("  (BROKER push requires LV1 data permission — this account has LV2)")
            print("  See BrokerHandlerBase for the push-based alternative.")
        else:
            # data is (bid_df, ask_df) tuple
            if isinstance(data, tuple) and len(data) == 2:
                print_broker_queue(data[0], "BID")
                print_broker_queue(data[1], "ASK")
            elif isinstance(data, dict):
                print_broker_queue(data.get("bid"), "BID")
                print_broker_queue(data.get("ask"), "ASK")
            else:
                print(f"  {data}")
        print()

    ctx.close()
    print("Done.")


if __name__ == "__main__":
    main()
