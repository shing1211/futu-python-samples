"""Market Breadth Dashboard.

Tracks market breadth indicators across multiple markets: advancing/declining
issues, new highs/lows, volume distribution, and sector participation.

Usage:
    python3 main.py [--markets HK,US,SH,SZ]
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


# ---------------------------------------------------------------------------
# Breadth computation
# ---------------------------------------------------------------------------

def compute_breadth(quote_ctx, market_name, market_enum):
    """Compute breadth indicators for a given market.

    Returns dict with advancing/declining counts, new highs/lows,
    up/down volume, and sector breakdown.
    """
    result = {
        "market": market_name,
        "advancing": 0,
        "declining": 0,
        "unchanged": 0,
        "advancing_volume": 0,
        "declining_volume": 0,
        "new_highs": 0,
        "new_lows": 0,
        "total_volume": 0,
        "total_value": 0.0,
        "sectors": defaultdict(lambda: {"up": 0, "down": 0, "unchanged": 0}),
        "stock_count": 0,
    }

    # Get all stock list for this market
    ret, stock_list = quote_ctx.get_stock_list(market=market_enum)
    if ret != ft.RetCode.SUCCESS or stock_list is None or stock_list.empty:
        logger.warning("Cannot get stock list for %s", market_name)
        return None

    codes = stock_list["code"].tolist()
    result["stock_count"] = len(codes)

    if not codes:
        return result

    # Fetch quotes in batches
    BATCH = 200
    for i in range(0, len(codes), BATCH):
        batch = codes[i:i + BATCH]
        ret, quotes = quote_ctx.get_stock_quote(batch)
        if ret != ft.RetCode.SUCCESS or quotes is None or quotes.empty:
            continue

        for _, row in quotes.iterrows():
            code = str(row.get("code", ""))
            last = float(row.get("last_price", 0) or 0)
            open_p = float(row.get("open_price", 0) or 0)
            high = float(row.get("high_price", 0) or 0)
            low = float(row.get("low_price", 0) or 0)
            volume = float(row.get("volume", 0) or 0)
            turnover = float(row.get("turnover", 0) or 0)

            result["total_volume"] += int(volume)
            result["total_value"] += turnover

            if last > open_p + 1e-6:
                result["advancing"] += 1
                result["advancing_volume"] += int(volume)
            elif last < open_p - 1e-6:
                result["declining"] += 1
                result["declining_volume"] += int(volume)
            else:
                result["unchanged"] += 1

            # Simple new high/low detection (using today's range vs last price)
            # In production, this would compare against historical highs/lows
            if high > last * 1.05:  # heuristic proxy
                result["new_highs"] += 1
            if low < last * 0.95:
                result["new_lows"] += 1

            # Sector classification (use plate info if available)
            # For now, classify by stock code prefix as a proxy
            if code.startswith("0"):
                sector = "Main Board"
            elif code.startswith("8"):
                sector = "GEM"
            elif code.startswith("9"):
                sector = "Enterprise"
            else:
                sector = "Other"

            if last > open_p + 1e-6:
                result["sectors"][sector]["up"] += 1
            elif last < open_p - 1e-6:
                result["sectors"][sector]["down"] += 1
            else:
                result["sectors"][sector]["unchanged"] += 1

    return result


def format_breadth_bar(ratio, width=20):
    """Format a horizontal breadth bar."""
    filled = int(abs(ratio) * width)
    filled = min(filled, width)
    if ratio >= 0:
        return "█" * filled + "░" * (width - filled)
    else:
        return "░" * (width - filled) + "█" * filled


def print_breadth_report(breadth):
    """Print a formatted breadth report."""
    b = breadth
    total = b["advancing"] + b["declining"] + b["unchanged"]
    if total == 0:
        print(f"  No data available for {b['market']}")
        return

    adv_pct = b["advancing"] / total * 100
    dec_pct = b["declining"] / total * 100
    adv_dec_ratio = b["advancing"] / max(b["declining"], 1)

    # McClellan Oscillator approximation
    mcclellan = (b["advancing"] - b["declining"]) / total * 100

    print(f"\n  ── {b['market']} Market Breadth ──")
    print(f"  Stocks: {total:,}  (▲ {b['advancing']:,}  ▼ {b['declining']:,}  ─ {b['unchanged']:,})")
    print(f"  Adv/Dec Ratio: {adv_dec_ratio:.2f}")
    print(f"  McClellan:     {mcclellan:+.1f}%")

    # Breadth thrust
    if mcclellan > 5:
        signal = "🟢 BREADTH THRUST (strong advance)"
    elif mcclellan < -5:
        signal = "🔴 BREADTH EXHAUSTION (strong decline)"
    elif mcclellan > 0:
        signal = "🟡 Positive breadth"
    else:
        signal = "🟡 Negative breadth"
    print(f"  Signal: {signal}")

    # Advancing/Declining volume
    total_vol = b["advancing_volume"] + b["declining_volume"]
    if total_vol > 0:
        adv_vol_pct = b["advancing_volume"] / total_vol * 100
        dec_vol_pct = b["declining_volume"] / total_vol * 100
        print(f"\n  Volume: ▲ {adv_vol_pct:.0f}%  ▼ {dec_vol_pct:.0f}%")

        vol_bar = format_breadth_bar(
            (b["advancing_volume"] - b["declining_volume"]) / max(total_vol, 1)
        )
        print(f"         {vol_bar}")

    # Volume summary
    print(f"\n  Total Volume:  {b['total_volume']:,}")
    print(f"  Total Value:   ${b['total_value']:,.0f}")
    print(f"  New Highs:     {b['new_highs']:,}")
    print(f"  New Lows:      {b['new_lows']:,}")

    # Sector breakdown
    if b["sectors"]:
        print(f"\n  Sector Breakdown:")
        for sector, counts in sorted(b["sectors"].items()):
            s_total = counts["up"] + counts["down"] + counts["unchanged"]
            if s_total == 0:
                continue
            up_pct = counts["up"] / s_total * 100
            bar = format_breadth_bar(counts["up"] / max(counts["down"], 1) - 1, 10)
            print(f"    {sector:<14} ▲{counts['up']:>3}  ▼{counts['down']:>3}  ─{counts['unchanged']:>3}  {bar} ({up_pct:.0f}% up)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Market Breadth Dashboard")
    parser.add_argument("--markets", default="HK,US",
                        help="Comma-separated market codes: HK,US,SH,SZ")
    args = parser.parse_args()

    selected = [m.strip().upper() for m in args.markets.split(",")]

    quote_ctx = create_quote_context()

    try:
        print(f"\n{'='*60}")
        print(f"  📊 MARKET BREADTH DASHBOARD")
        print(f"  Markets: {', '.join(selected)}")
        print(f"{'='*60}")

        for market_name in selected:
            market_enum = MARKET_CODES.get(market_name)
            if market_enum is None:
                logger.warning("Unknown market: %s (skip, use HK/US/SH/SZ)", market_name)
                continue

            breadth = compute_breadth(quote_ctx, market_name, market_enum)
            if breadth:
                print_breadth_report(breadth)

        print()

    finally:
        quote_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()