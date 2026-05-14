"""52-Week High/Low Scanner — Screening.

Identifies stocks near their 52-week extremes with volume confirmation.
Flags potential breakouts above 52-week highs and reversals near 52-week lows.

Usage:
    python3 main.py [--markets HK US] [--threshold 0.95] [--volume-ratio 1.5]
"""

import sys
import os
import logging
import argparse

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
DEFAULT_MARKETS = ["HK", "US"]
DEFAULT_THRESHOLD = 0.95    # flag stocks above 95% of 52-week high
DEFAULT_VOLUME_RATIO = 1.5  # volume must be 1.5× average
WEEKS = 52
MIN_BARS = WEEKS * 3 // 5  # ~30 bars minimum (skip delisted/suspended)

MARKET_ENUM = {
    "HK": ft.Market.HK,
    "US": ft.Market.US,
    "SH": ft.Market.SH,
    "SZ": ft.Market.SZ,
}


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def scan_stock(quote_ctx, code, threshold, vol_ratio_threshold):
    """Scan a single stock for proximity to 52-week extremes.

    Returns dict with scan results or None if insufficient data.
    """
    # Fetch daily K-lines
    closes = []
    volumes = []
    next_token = ""
    for _ in range(5):
        ret, df, next_page = quote_ctx.request_history_kline(
            code=code, start=next_token, num_bars=50,
            ktype=ft.KLType.K_DAY,
        )
        if ret != ft.RetCode.SUCCESS:
            return None
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                closes.append(float(row["close"]))
                volumes.append(float(row.get("volume", 0) or 0))
        if not next_page:
            break
        next_token = next_page

    if len(closes) < MIN_BARS:
        return None

    high_52w = max(closes)
    low_52w = min(closes)
    current_price = closes[-1]
    current_volume = volumes[-1] if volumes else 0
    avg_volume = statistics_mean(volumes[-20:]) if len(volumes) >= 10 else 0

    # Distance from extremes
    price_range = high_52w - low_52w
    if price_range < 1e-6:
        return None

    dist_from_high = (high_52w - current_price) / price_range
    dist_from_low = (current_price - low_52w) / price_range

    # Proximity score (1.0 = at the extreme)
    proximity_high = 1.0 - dist_from_high  # high when near 52w high
    proximity_low = 1.0 - dist_from_low    # high when near 52w low

    # Volume confirmation
    vol_confirmed = (avg_volume > 0 and
                     current_volume >= avg_volume * vol_ratio_threshold)

    return {
        "code": code,
        "high_52w": high_52w,
        "low_52w": low_52w,
        "current": current_price,
        "proximity_high": proximity_high,
        "proximity_low": proximity_low,
        "vol_ratio": current_volume / max(avg_volume, 1),
        "vol_confirmed": vol_confirmed,
        "near_high": proximity_high >= threshold,
        "near_low": proximity_low >= threshold,
    }


def statistics_mean(vals):
    """Pure stdlib mean."""
    if not vals:
        return 0
    return sum(vals) / len(vals)


def format_scan_report(results):
    """Format scanner results."""
    near_high = [r for r in results if r["near_high"]]
    near_low = [r for r in results if r["near_low"]]

    lines = []

    if near_high:
        lines.append(f"\n  ── 🔥 Near 52-Week High ({len(near_high)} stocks) ──")
        lines.append(
            f"  {'Code':<10} {'Last':>10} {'52W High':>10} "
            f"{'Proximity':>10} {'Vol Ratio':>10} {'Signal'}"
        )
        lines.append(f"  {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*15}")
        for r in sorted(near_high, key=lambda x: x["proximity_high"], reverse=True)[:15]:
            signal = "🚀 BREAKOUT" if r["vol_confirmed"] else "⚠️ WATCH"
            lines.append(
                f"  {r['code']:<10} {r['current']:>10.2f} {r['high_52w']:>10.2f} "
                f"{r['proximity_high']:>9.0%} {r['vol_ratio']:>9.1f}x {signal}"
            )

    if near_low:
        lines.append(f"\n  ── 🕳️ Near 52-Week Low ({len(near_low)} stocks) ──")
        lines.append(
            f"  {'Code':<10} {'Last':>10} {'52W Low':>10} "
            f"{'Proximity':>10} {'Vol Ratio':>10} {'Signal'}"
        )
        lines.append(f"  {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*15}")
        for r in sorted(near_low, key=lambda x: x["proximity_low"], reverse=True)[:15]:
            signal = "🛑 REVERSAL?" if r["vol_confirmed"] else "⚠️ WATCH"
            lines.append(
                f"  {r['code']:<10} {r['current']:>10.2f} {r['low_52w']:>10.2f} "
                f"{r['proximity_low']:>9.0%} {r['vol_ratio']:>9.1f}x {signal}"
            )

    if not near_high and not near_low:
        lines.append("\n  No stocks near 52-week extremes with current criteria.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="52-Week High/Low Scanner")
    parser.add_argument("--markets", nargs="+", default=DEFAULT_MARKETS,
                        help="Markets to scan: HK US SH SZ")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                        help="Proximity threshold (0.95 = top 5%% near high)")
    parser.add_argument("--volume-ratio", type=float, default=DEFAULT_VOLUME_RATIO,
                        help="Min volume ratio to flag breakout")
    args = parser.parse_args()

    markets = [m.upper() for m in args.markets]
    threshold = args.threshold
    vol_ratio = args.volume_ratio

    quote_ctx = create_quote_context()

    try:
        print(f"\n{'='*70}")
        print(f"  📊 52-WEEK HIGH/LOW SCANNER")
        print(f"  Markets: {', '.join(markets)}  |  Threshold: {threshold:.0%}  "
              f"|  Vol ratio: {vol_ratio:.1f}x")
        print(f"{'='*70}")

        all_results = []

        for market_name in markets:
            market_enum = MARKET_ENUM.get(market_name)
            if market_enum is None:
                continue

            # Get stock list
            ret, stock_list = quote_ctx.get_stock_list(market=market_enum)
            if ret != ft.RetCode.SUCCESS or stock_list is None:
                continue

            codes = stock_list["code"].tolist()
            logger.info("Scanning %d stocks in %s …", len(codes), market_name)
            print(f"\n  Scanning {len(codes)} stocks in {market_name} market …")

            BATCH = 200
            for i in range(0, len(codes), BATCH):
                batch_codes = codes[i:i + BATCH]
                # Quick quote to get current prices
                ret_q, df_q = quote_ctx.get_stock_quote(batch_codes)
                if ret_q != ft.RetCode.SUCCESS or df_q is None or df_q.empty:
                    continue

                for _, row in df_q.iterrows():
                    code = row.get("code", "")
                    result = scan_stock(quote_ctx, code, threshold, vol_ratio)
                    if result and (result["near_high"] or result["near_low"]):
                        result["name"] = str(row.get("stock_name", ""))[:12]
                        result["market"] = market_name
                        all_results.append(result)

        print(format_scan_report(all_results))
        print(f"\n{'='*70}\n")

    finally:
        quote_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()