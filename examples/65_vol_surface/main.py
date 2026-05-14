#!/usr/bin/env python3
"""
65 — Volatility Surface Builder

Fetch option chains across all available expirations, extract implied
volatility per strike, and display a moneyness × expiry IV matrix.

No order placement — pure data analysis.

SDK: OpenQuoteContext.get_option_expiration_date()
               .get_option_chain()
               .get_stock_quote()
"""

import sys
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

STOCK = "US.NVDA"
MAX_EXPIRIES = 10
MONEYNESS_MIN = 0.7
MONEYNESS_MAX = 1.3
MONEYNESS_BUCKETS = [0.80, 0.90, 0.95, 1.00, 1.05, 1.10, 1.20]


def bucket_moneyness(strike: float, spot: float) -> float:
    if spot <= 0:
        return 0.0
    return strike / spot


def assign_bucket(moneyness: float) -> str:
    for b in MONEYNESS_BUCKETS:
        if moneyness <= b:
            return f"{b:.2f}x"
    return f"{MONEYNESS_BUCKETS[-1]:.2f}x+"


def main():
    print(f"  === Volatility Surface Builder ===\n")
    print(f"  Stock: {STOCK}\n")

    ctx = create_quote_context()

    try:
        ret, quotes = ctx.get_stock_quote([STOCK])
        if ret != 0 or quotes is None or quotes.empty:
            print(f"  get_stock_quote failed: {quotes}")
            return
        spot = float(quotes.iloc[0].get("last_price", 0))
        if spot <= 0:
            print(f"  No valid price for {STOCK}")
            return
        print(f"  Spot price: {spot:.2f}\n")

        ret, expirations = ctx.get_option_expiration_date(STOCK)
        if ret != 0:
            print(f"  get_option_expiration_date failed: {expirations}")
            return

        if hasattr(expirations, "empty") and expirations.empty:
            print(f"  No expirations for {STOCK}")
            return

        dates = []
        if isinstance(expirations, list):
            dates = expirations[:MAX_EXPIRIES]
        elif hasattr(expirations, "iloc"):
            for _, row in expirations.head(MAX_EXPIRIES).iterrows():
                d = row.get("strike_time", "")
                dist = row.get("option_expiry_date_distance", 0)
                if d:
                    dates.append((str(d), int(dist)))
        else:
            print(f"  Unexpected expiration format: {type(expirations)}")
            return

        print(f"  Expirations: {len(dates)}")
        for d, dist in dates:
            print(f"    {d} ({dist} days)")
        print()

        header_buckets = "  " + "".join(f"{b:>8}" for b in MONEYNESS_BUCKETS)
        print(f"  {'Expiry':<16}{header_buckets}")
        print(f"  {'-'*16}" + "-" * 8 * len(MONEYNESS_BUCKETS))

        for expiry_date, days_to in dates:
            bucket_ivs: dict[str, list[float]] = {f"{b:.2f}x": [] for b in MONEYNESS_BUCKETS}
            bucket_ivs[f"{MONEYNESS_BUCKETS[-1]:.2f}x+"] = []

            ret, chain = ctx.get_option_chain(
                STOCK, start=expiry_date, end=expiry_date, option_type=ft.OptionType.CALL,
            )
            if ret != 0 or chain is None or chain.empty:
                continue

            for _, row in chain.iterrows():
                strike = float(row.get("strike_price", 0))
                iv = float(row.get("implied_volatility", 0))
                if strike <= 0 or iv <= 0:
                    continue

                mn = bucket_moneyness(strike, spot)
                if mn < MONEYNESS_MIN or mn > MONEYNESS_MAX:
                    continue

                bucket_key = assign_bucket(mn)
                if bucket_key in bucket_ivs:
                    bucket_ivs[bucket_key].append(iv)

            row_parts = [f"  {expiry_date:<14}"]
            for b in MONEYNESS_BUCKETS:
                key = f"{b:.2f}x"
                vals = bucket_ivs[key]
                if vals:
                    avg_iv = sum(vals) / len(vals) * 100
                    row_parts.append(f"{avg_iv:>7.1f}%")
                else:
                    row_parts.append(f"{'—':>8}")
            key_plus = f"{MONEYNESS_BUCKETS[-1]:.2f}x+"
            vals = bucket_ivs[key_plus]
            if vals:
                avg_iv = sum(vals) / len(vals) * 100
                row_parts.append(f"{avg_iv:>7.1f}%")
            else:
                row_parts.append(f"{'—':>8}")

            print("".join(row_parts))

        print()
        print(f"  Moneyness: strike / spot. Buckets: {', '.join(f'{b:.2f}' for b in MONEYNESS_BUCKETS)}")

    finally:
        ctx.close()


if __name__ == "__main__":
    main()
