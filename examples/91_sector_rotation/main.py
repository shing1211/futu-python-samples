"""Sector Rotation Scanner — Screening.

Ranks all sector/industry plates by relative strength using RSI and
price momentum. Identifies leading and lagging sectors for rotation signals.

Usage:
    python3 main.py [--market HK] [--rsi-period 14] [--lookback 30]
"""

import sys
import os
import logging
import argparse
import statistics

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
DEFAULT_MARKET = "HK"
DEFAULT_RSI_PERIOD = 14
DEFAULT_LOOKBACK = 30

MARKET_ENUM = {
    "HK": ft.Market.HK,
    "US": ft.Market.US,
    "SH": ft.Market.SH,
    "SZ": ft.Market.SZ,
}


# ---------------------------------------------------------------------------
# RSI computation
# ---------------------------------------------------------------------------

def compute_rsi(values, period):
    """Compute RSI from a list of price changes."""
    if len(values) < period + 1:
        return None

    gains = []
    losses = []
    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        if delta > 0:
            gains.append(delta)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(delta))

    if len(gains) < period:
        return None

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def get_plates(quote_ctx, market_enum):
    """Get all plates for a market."""
    ret, df = quote_ctx.get_plate_list(market=market_enum)
    if ret != ft.RetCode.SUCCESS or df is None or df.empty:
        logger.warning("Cannot get plate list for market %s", market_enum)
        return []
    return df.to_dict("records")


def get_plate_stocks(quote_ctx, plate_code, market_enum):
    """Get all stocks in a plate."""
    ret, df = quote_ctx.get_plate_stock(code_list=[plate_code], market=market_enum)
    if ret != ft.RetCode.SUCCESS or df is None or df.empty:
        return []
    return [row.get("code", "") for row in df.to_dict("records")]


def compute_sector_rsi(quote_ctx, plate_code, market_enum, rsi_period, lookback):
    """Compute aggregate RSI for all stocks in a plate.

    Returns average RSI, number of stocks, and top movers.
    """
    stocks = get_plate_stocks(quote_ctx, plate_code, market_enum)
    if not stocks:
        return None

    rsi_values = []
    movers = []

    # Process in batches
    BATCH = 50
    for i in range(0, len(stocks), BATCH):
        batch = stocks[i:i + BATCH]
        ret, quotes = quote_ctx.get_stock_quote(batch)
        if ret != ft.RetCode.SUCCESS or quotes is None or quotes.empty:
            continue

        for _, row in quotes.iterrows():
            code = row.get("code", "")
            close = float(row.get("last_price", 0) or 0)
            if close <= 0:
                continue

            # Fetch recent K-lines for RSI
            kl_ret, kl_df, _ = quote_ctx.request_history_kline(
                code=code, num_bars=lookback + rsi_period + 5,
                ktype=ft.KLType.K_DAY,
            )
            if kl_ret != ft.RetCode.SUCCESS or kl_df is None or kl_df.empty:
                continue

            closes = kl_df["close"].tolist()
            rsi = compute_rsi(closes, rsi_period)
            if rsi is not None:
                rsi_values.append(rsi)
                prev_close = closes[-2] if len(closes) >= 2 else close
                daily_return = (close - prev_close) / prev_close * 100 if prev_close > 0 else 0
                movers.append({
                    "code": code,
                    "name": str(row.get("stock_name", ""))[:12],
                    "rsi": rsi,
                    "return_pct": daily_return,
                    "price": close,
                })

    if not rsi_values:
        return None

    avg_rsi = statistics.mean(rsi_values)
    count = len(rsi_values)

    # Top 3 movers
    movers.sort(key=lambda x: x["return_pct"], reverse=True)
    top_gainers = movers[:3]
    top_losers = sorted(movers, key=lambda x: x["return_pct"])[:3]

    return {
        "plate_code": plate_code,
        "avg_rsi": avg_rsi,
        "stock_count": count,
        "top_gainers": top_gainers,
        "top_losers": top_losers,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Sector Rotation Scanner")
    parser.add_argument("--market", default=DEFAULT_MARKET,
                        help="Market code: HK, US, SH, SZ")
    parser.add_argument("--rsi-period", type=int, default=DEFAULT_RSI_PERIOD,
                        help="RSI period (default 14)")
    parser.add_argument("--lookback", type=int, default=DEFAULT_LOOKBACK,
                        help="K-line lookback for RSI (default 30)")
    args = parser.parse_args()

    market_enum = MARKET_ENUM.get(args.market.upper())
    if market_enum is None:
        logger.error("Invalid market: %s (use HK, US, SH, SZ)", args.market)
        return

    quote_ctx = create_quote_context()

    try:
        print(f"\n{'='*70}")
        print(f"  🔄 SECTOR ROTATION SCANNER — {args.market}")
        print(f"  RSI period: {args.rsi_period}  Lookback: {args.lookback} bars")
        print(f"{'='*70}")

        # ── Get plates ──────────────────────────────────────────────────
        plates = get_plates(quote_ctx, market_enum)
        if not plates:
            logger.warning("No plates found for %s", args.market)
            return

        logger.info("Found %d plates in %s market", len(plates), args.market)
        print(f"\n  Scanning {len(plates)} plates …\n")

        results = []
        for plate in plates:
            plate_code = plate.get("code", "")
            plate_name = plate.get("plate_name", plate_code)

            data = compute_sector_rsi(
                quote_ctx, plate_code, market_enum,
                args.rsi_period, args.lookback,
            )
            if data:
                data["plate_name"] = plate_name
                results.append(data)
                print(f"  ✅ {plate_name:<20} RSI={data['avg_rsi']:>5.1f}  "
                      f"({data['stock_count']} stocks)")

        if not results:
            print("  No plates with sufficient data.")
            return

        # ── Rank: oversold first (lowest RSI = rotation candidates) ────
        results.sort(key=lambda x: x["avg_rsi"])

        print(f"\n{'='*70}")
        print(f"  📊 SECTOR RANKING (lowest RSI → rotation in candidates)")
        print(f"{'='*70}")
        print(f"  {'Rank':<5} {'Sector':<22} {'RSI':>6} {'Stocks':>7}  {'Signal'}")
        print(f"  {'-'*5} {'-'*22} {'-'*6} {'-'*7}  {'-'*20}")

        for i, r in enumerate(results):
            rsi = r["avg_rsi"]
            if rsi < 30:
                signal = "🔴 OVERSOLD — BUY CANDIDATE"
            elif rsi < 50:
                signal = "🟡 NEUTRAL"
            elif rsi > 70:
                signal = "🟢 OVERBOUGHT — MAY ROTATE OUT"
            else:
                signal = "⚪ WATCHING"

            print(f"  {i+1:<5} {r['plate_name']:<22} {rsi:>6.1f} {r['stock_count']:>7}  {signal}")

        # ── Detail for top candidates ───────────────────────────────────
        print(f"\n{'='*70}")
        print(f"  🔍 TOP ROTATION CANDIDATES (RSI < 40)")
        print(f"{'='*70}")

        candidates = [r for r in results if r["avg_rsi"] < 40][:5]
        for r in candidates:
            print(f"\n  📌 {r['plate_name']} (RSI {r['avg_rsi']:.1f})")
            print(f"     Top Gainers:")
            for g in r["top_gainers"][:3]:
                print(f"       ▲ {g['code']:<10} {g['name']:<12} "
                      f"RSI={g['rsi']:.1f}  +{g['return_pct']:.1f}% @ {g['price']:.2f}")
            print(f"     Top Losers:")
            for l in r["top_losers"][:3]:
                print(f"       ▼ {l['code']:<10} {l['name']:<12} "
                      f"RSI={l['rsi']:.1f}  {l['return_pct']:.1f}% @ {l['price']:.2f}")

        print()

    finally:
        quote_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()