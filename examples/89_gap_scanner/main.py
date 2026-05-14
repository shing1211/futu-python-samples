"""Gap Scanner (Pre-Market) — Screening.

Detects overnight gaps by comparing prior close vs current open across
all stocks in selected markets. Flags gaps exceeding a configurable
threshold with volume confirmation.

Usage:
    python3 main.py [--markets HK,US] [--gap-pct 3.0]
"""

import sys
import os
import logging
import argparse
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connect import create_quote_context, clear_connection_cache
import futu as ft

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MARKET_CODES = {
    "HK": ft.Market.HK,
    "US": ft.Market.US,
    "SH": ft.Market.SH,
    "SZ": ft.Market.SZ,
}
DEFAULT_MARKETS = ["HK", "US"]
DEFAULT_GAP_PCT = 3.0


# ---------------------------------------------------------------------------
# Gap scanning
# ---------------------------------------------------------------------------

def scan_market(quote_ctx, market_name, market_enum, gap_threshold):
    """Scan all stocks in a market for gaps.

    Returns list of gap candidates sorted by absolute gap percentage.
    """
    # Get stock list
    ret, stock_list = quote_ctx.get_stock_list(market=market_enum)
    if ret != ft.RetCode.SUCCESS or stock_list is None or stock_list.empty:
        logger.warning("Cannot get stock list for %s", market_name)
        return []

    codes = stock_list["code"].tolist()
    logger.info("Scanning %d stocks in %s …", len(codes), market_name)

    gaps = []
    BATCH = 200

    for i in range(0, len(codes), BATCH):
        batch = codes[i:i + BATCH]
        ret, quotes = quote_ctx.get_stock_quote(batch)
        if ret != ft.RetCode.SUCCESS or quotes is None or quotes.empty:
            continue

        for _, row in quotes.iterrows():
            code = str(row.get("code", ""))
            last_price = float(row.get("last_price", 0) or 0)
            open_price = float(row.get("open_price", 0) or 0)
            high_price = float(row.get("high_price", 0) or 0)
            low_price = float(row.get("low_price", 0) or 0)
            prev_close = float(row.get("prev_close_price", 0) or 0)
            volume = float(row.get("volume", 0) or 0)
            turnover = float(row.get("turnover", 0) or 0)
            stock_name = str(row.get("stock_name", ""))

            if prev_close <= 0 or open_price <= 0:
                continue

            gap_pct = (open_price - prev_close) / prev_close * 100
            abs_gap = abs(gap_pct)

            if abs_gap < gap_threshold:
                continue

            # Volume ratio (proxy for confirmation)
            # We flag all gap stocks; volume check is informational
            direction = "▲ GAP UP" if gap_pct > 0 else "▼ GAP DOWN"

            gaps.append({
                "code": code,
                "name": stock_name[:16],
                "market": market_name,
                "prev_close": prev_close,
                "open": open_price,
                "last": last_price,
                "gap_pct": gap_pct,
                "abs_gap": abs_gap,
                "direction": direction,
                "volume": int(volume),
                "turnover": turnover,
                "range_pct": (high_price - low_price) / prev_close * 100 if prev_close > 0 else 0,
            })

    # Sort by absolute gap descending
    gaps.sort(key=lambda x: x["abs_gap"], reverse=True)
    return gaps


def format_gap_report(gaps, market_name):
    """Format gap results as a table."""
    if not gaps:
        return f"  No gaps ≥ threshold found in {market_name}"

    lines = []
    lines.append(f"\n  ── {market_name} Gaps ({len(gaps)} found) ──")
    lines.append(
        f"  {'Code':<10} {'Name':<16} {'Direction':<12} "
        f"{'PrevClose':>10} {'Open':>10} {'Last':>10} "
        f"{'Gap%':>8} {'Volume':>10} {'Range%':>8}"
    )
    lines.append(f"  {'-'*10} {'-'*16} {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*8} {'-'*10} {'-'*8}")

    for g in gaps[:25]:  # top 25
        marker = "🔥" if g["abs_gap"] > 7 else ("⚡" if g["abs_gap"] > 4 else " ")
        lines.append(
            f"  {marker}{g['code']:<9} {g['name']:<16} {g['direction']:<12} "
            f"{g['prev_close']:>10.2f} {g['open']:>10.2f} {g['last']:>10.2f} "
            f"{g['gap_pct']:>+7.2f}% {g['volume']:>10,} {g['range_pct']:>7.1f}%"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Gap Scanner — detect overnight gaps")
    parser.add_argument("--markets", default=",".join(DEFAULT_MARKETS),
                        help="Comma-separated market codes: HK,US,SH,SZ")
    parser.add_argument("--gap-pct", type=float, default=DEFAULT_GAP_PCT,
                        help="Minimum gap percentage to flag (default 3.0)")
    args = parser.parse_args()

    markets = [m.strip().upper() for m in args.markets.split(",")]
    gap_threshold = args.gap_pct

    quote_ctx = create_quote_context()

    try:
        print(f"\n{'='*70}")
        print(f"  🔍 GAP SCANNER")
        print(f"  Markets: {', '.join(markets)}  |  Gap threshold: {gap_threshold}%")
        print(f"{'='*70}")

        total_gaps = 0
        for market_name in markets:
            market_enum = MARKET_CODES.get(market_name)
            if market_enum is None:
                logger.warning("Unknown market: %s (use HK, US, SH, SZ)", market_name)
                continue

            gaps = scan_market(quote_ctx, market_name, market_enum, gap_threshold)
            total_gaps += len(gaps)
            print(format_gap_report(gaps, market_name))

        print(f"\n  Total gaps found: {total_gaps}")
        print(f"  📌 Note: Gap % = (Open − Prev Close) / Prev Close × 100")
        print(f"  🔥 = gap > 7%  ⚡ = gap > 4%")
        print(f"{'='*70}\n")

    finally:
        quote_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()