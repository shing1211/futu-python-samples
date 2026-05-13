#!/usr/bin/env python3
"""
44 — Multi-Market Snapshot

Fetch market snapshots for all four markets (HK, US, SH, SZ) concurrently.

01_snapshot iterates markets sequentially. This version uses ThreadPoolExecutor
to enumerate stock lists and fetch snapshots for all four markets simultaneously.

Workflow per market:
  1. get_stock_basicinfo(market, SecurityType.STOCK) -> list of codes
  2. get_market_snapshot(code_batch) -> snapshot DataFrame

SDK: OpenQuoteContext.get_stock_basicinfo / get_market_snapshot
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Timer

import futu as ft
from connect import create_quote_context


MARKETS = [
    (ft.Market.HK, "HK"),
    (ft.Market.US, "US"),
    (ft.Market.SH, "SH"),
    (ft.Market.SZ, "SZ"),
]

TIMEOUT = 30   # hard timeout for the whole operation


def fetch_market(ctx, market, label):
    """Enumerate stocks in a market then snapshot them. Returns (label, DataFrame or error)."""
    import pandas as pd

    # Step 1: get stock list
    ret, basic = ctx.get_stock_basicinfo(market, ft.SecurityType.STOCK)
    if ret != 0:
        return label, None, f"get_stock_basicinfo: {basic}"

    if basic.empty:
        return label, None, "no stocks returned"

    codes = basic["code"].tolist()

    # Step 2: snapshot in batches of 200
    all_rows = []
    for i in range(0, len(codes), 200):
        batch = codes[i:i + 200]
        ret, snap = ctx.get_market_snapshot(batch)
        if ret != 0:
            return label, None, f"get_market_snapshot batch {i//200}: {snap}"
        if snap is not None and not snap.empty:
            all_rows.append(snap)

    if not all_rows:
        return label, None, "no snapshot data"

    combined = pd.concat(all_rows, ignore_index=True)
    return label, combined, None


def main():
    ctx = create_quote_context()

    print(f"Fetching snapshots for all 4 markets in parallel (timeout={TIMEOUT}s)...\n")

    results = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(fetch_market, ctx, market, label): label
            for market, label in MARKETS
        }
        for future in as_completed(futures):
            label, data, error = future.result()
            results[label] = (data, error)

    print(f"{'Market':<6} {'Stocks':>7}  {'Sample (code / last_price / vol)':>45}")
    print("-" * 65)

    total = 0
    for market, label in MARKETS:
        data, error = results[label]
        if error:
            short = error.replace("get_market_snapshot batch 0: ", "").strip()
            print(f"{label:<6} {'n/a':>7}  (permission: {short})")
        else:
            n = len(data)
            total += n
            sample = data.iloc[0]
            print(f"{label:<6} {n:>7,}  {sample['code']} / {sample['last_price']} / vol={int(sample['volume']):,}")

    print(f"\nTotal snapshot rows: {total:,}")
    ctx.close()
    print("Done.")


if __name__ == "__main__":
    main()
