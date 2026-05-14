"""VWAP Execution Analysis — SIMULATE only.

Compares your execution prices against the Volume-Weighted Average Price
(VWAP) to measure execution quality. Computes slippage, timing cost, and
shows a visual breakdown of how well you captured the benchmark price.

Usage:
    python3 main.py --buy-trades SAMPLE_BUY.csv --sell-trades SAMPLE_SELL.csv
    python3 main.py --generate-sample        # create sample CSV files first
"""

import sys
import os
import logging
import argparse
import csv
import math
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connect import create_quote_context, clear_connection_cache
import futu as ft

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DEFAULT_STOCK = "HK.00700"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def generate_sample_csv(filename, side="buy", num_trades=20):
    """Generate a sample CSV of trade fills for testing."""
    import random
    random.seed(42)

    base_price = 200.0
    trades = []
    for i in range(num_trades):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        price = round(base_price + random.uniform(-5, 5) + (i * 0.1), 4)
        qty = random.choice([100, 200, 300, 500, 1000])
        trades.append({
            "timestamp": timestamp,
            "code": DEFAULT_STOCK,
            "side": side.upper(),
            "price": price,
            "qty": qty,
        })

    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "code", "side", "price", "qty"])
        writer.writeheader()
        writer.writerows(trades)

    logger.info("Generated %d sample trades in %s", num_trades, filename)
    return trades


def load_trades_from_csv(filepath):
    """Load trades from a CSV file. Returns list of dicts."""
    trades = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            trades.append({
                "timestamp": row["timestamp"],
                "code": row["code"],
                "side": row["side"].upper(),
                "price": float(row["price"]),
                "qty": int(row["qty"]),
            })
    return trades


def compute_vwap(trades):
    """Compute VWAP from a list of trades.

    VWAP = Σ(price × qty) / Σ(qty)
    """
    total_value = sum(t["price"] * t["qty"] for t in trades)
    total_qty = sum(t["qty"] for t in trades)
    if total_qty == 0:
        return 0
    return total_value / total_qty


def compute_slippage(trades, benchmark_price):
    """Compute slippage for each trade vs benchmark.

    Slippage = (exec_price - benchmark) / benchmark × 100
    Positive = paid more than benchmark (bad for buys)
    Negative = paid less than benchmark (good for buys)
    """
    results = []
    for t in trades:
        slip = (t["price"] - benchmark_price) / benchmark_price * 100
        cost_impact = slip * t["qty"] * benchmark_price / 100  # dollar impact
        results.append({
            **t,
            "slippage_pct": slip,
            "cost_impact": cost_impact,
        })
    return results


def time_bucket_analysis(trades, interval_minutes=5):
    """Analyze execution quality by time buckets.

    Shows VWAP slippage per time window to identify optimal execution times.
    """
    if not trades:
        return []

    from collections import defaultdict
    buckets = defaultdict(list)

    for t in trades:
        try:
            ts = datetime.strptime(t["timestamp"], "%Y-%m-%d %H:%M:%S")
            bucket_key = ts.replace(
                minute=(ts.minute // interval_minutes) * interval_minutes,
                second=0,
            ).strftime("%H:%M")
        except (ValueError, KeyError):
            bucket_key = "unknown"
        buckets[bucket_key].append(t)

    results = []
    for bucket in sorted(buckets.keys()):
        b_trades = buckets[bucket]
        b_vwap = compute_vwap(b_trades)
        b_total_qty = sum(t["qty"] for t in b_trades)
        b_avg_price = sum(t["price"] for t in b_trades) / len(b_trades)
        results.append({
            "bucket": bucket,
            "trades": len(b_trades),
            "total_qty": b_total_qty,
            "avg_price": round(b_avg_price, 4),
            "vwap": round(b_vwap, 4),
        })

    return results


def format_bar(value, max_val, width=30):
    """Format a horizontal bar for ASCII display."""
    if max_val == 0:
        return ""
    filled = int(abs(value) / max_val * width)
    filled = min(filled, width)
    if value >= 0:
        return "█" * filled
    else:
        return "░" * filled


# ---------------------------------------------------------------------------
# Live VWAP from market data
# ---------------------------------------------------------------------------

def fetch_live_market_data(quote_ctx, code, num_minutes=60):
    """Fetch recent K-line data for live VWAP computation.

    Uses get_rt_ticker for current price and recent K-lines for volume.
    """
    # Get current price
    ret, df = quote_ctx.get_stock_quote(code)
    if ret != ft.RetCode.SUCCESS:
        logger.error("Cannot fetch quote for %s", code)
        return None, None

    current_price = float(df.iloc[-1]["last_price"])
    current_volume = int(float(df.iloc[-1].get("volume", 0) or 0))

    # Get historical K-lines for volume profile
    bars = []
    next_token = ""
    for _ in range(3):
        ret, df_kl, next_token = quote_ctx.request_history_kline(
            code=code,
            start=next_token,
            num_bars=50,
            ktype=ft.KLType.K_1M,  # 1-minute bars
        )
        if ret != ft.RetCode.SUCCESS:
            break
        if df_kl is not None and not df_kl.empty:
            for _, row in df_kl.iterrows():
                bars.append({
                    "price": float(row["close"]),
                    "volume": float(row.get("volume", 0) or 0),
                })
        if not next_token:
            break

    return current_price, bars


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="VWAP Execution Analysis — measure trade quality vs benchmark")
    parser.add_argument("--buy-trades", default=None,
                        help="CSV file with buy trade fills")
    parser.add_argument("--sell-trades", default=None,
                        help="CSV file with sell trade fills")
    parser.add_argument("--generate-sample", action="store_true",
                        help="Generate sample CSV files for testing")
    parser.add_argument("--stock", default=DEFAULT_STOCK,
                        help="Stock code for live VWAP analysis")
    parser.add_argument("--live", action="store_true",
                        help="Run live VWAP analysis using market data")
    args = parser.parse_args()

    quote_ctx = create_quote_context()

    try:
        # ── Mode: Generate sample data ─────────────────────────────────
        if args.generate_sample:
            generate_sample_csv("sample_buy.csv", "buy", 20)
            generate_sample_csv("sample_sell.csv", "sell", 20)
            logger.info("Sample files created: sample_buy.csv, sample_sell.csv")
            logger.info("Run again with --buy-trades sample_buy.csv --sell-trades sample_sell.csv")
            return

        # ── Mode: Live VWAP ────────────────────────────────────────────
        if args.live:
            print(f"\n{'='*60}")
            print(f"  📊 LIVE VWAP ANALYSIS — {args.stock}")
            print(f"{'='*60}")

            current_price, bars = fetch_live_market_data(quote_ctx, args.stock)
            if current_price is None:
                logger.error("Cannot fetch live data. Exiting.")
                return

            if bars and len(bars) >= 5:
                live_vwap = sum(b["price"] * b["volume"] for b in bars) / sum(
                    b["volume"] for b in bars if b["volume"] > 0
                )
                print(f"\n  Current Price : {current_price:.4f}")
                print(f"  Live VWAP     : {live_vwap:.4f}")
                print(f"  Spread vs VWAP: {(current_price - live_vwap) / live_vwap * 100:+.2f}%")
                print(f"  Bars analysed : {len(bars)}")
            else:
                print(f"\n  Current Price : {current_price:.4f}")
                print(f"  Insufficient bar data for live VWAP ({len(bars)} bars)")

            print()
            return

        # ── Mode: CSV analysis ──────────────────────────────────────────
        if not args.buy_trades:
            parser.print_help()
            print("\n  Error: provide --buy-trades or use --generate-sample first")
            return

        # Load and analyse buy trades
        buy_trades = load_trades_from_csv(args.buy_trades)
        print(f"\n{'='*60}")
        print(f"  📊 VWAP EXECUTION ANALYSIS — {buy_trades[0]['code'] if buy_trades else 'N/A'}")
        print(f"{'='*60}")

        if buy_trades:
            buy_vwap = compute_vwap(buy_trades)
            buy_slippage = compute_slippage(buy_trades, buy_vwap)
            total_buy_qty = sum(t["qty"] for t in buy_trades)
            total_buy_cost = sum(t["price"] * t["qty"] for t in buy_trades)
            avg_slippage = sum(s["slippage_pct"] * s["qty"] for s in buy_slippage) / total_buy_qty
            total_cost_impact = sum(s["cost_impact"] for s in buy_slippage)

            print(f"\n  {'BUY TRADES':^56}")
            print(f"  {'-'*56}")
            print(f"  Number of trades  : {len(buy_trades)}")
            print(f"  Total quantity    : {total_buy_qty:,}")
            print(f"  Total cost        : ${total_buy_cost:,.2f}")
            print(f"  VWAP              : ${buy_vwap:.4f}")
            print(f"  Avg exec price    : ${total_buy_cost / total_buy_qty:.4f}")
            print(f"  Avg slippage      : {avg_slippage:+.3f}%")
            print(f"  Dollar impact     : ${total_cost_impact:+,.2f}")

            # Time bucket analysis
            print(f"\n  Execution by time bucket (5 min intervals):")
            buckets = time_bucket_analysis(buy_trades)
            if buckets:
                max_slip = max(abs(b.get("avg_price", 0) - buy_vwap) / buy_vwap * 100
                               for b in buckets if buy_vwap > 0) or 1
                for b in buckets:
                    diff = (b["avg_price"] - buy_vwap) / buy_vwap * 100
                    bar = format_bar(diff, max_slip, 20)
                    marker = "▸" if diff > 0 else "◂"
                    print(f"    {b['bucket']}  {b['trades']:>2} trades  qty={b['total_qty']:>6,}  "
                          f"avg={b['avg_price']:.2f}  Δ={diff:+.2f}% {marker} {bar}")

        # Load and analyse sell trades if provided
        if args.sell_trades:
            sell_trades = load_trades_from_csv(args.sell_trades)
            if sell_trades:
                sell_vwap = compute_vwap(sell_trades)
                sell_slippage = compute_slippage(sell_trades, sell_vwap)
                total_sell_qty = sum(t["qty"] for t in sell_trades)

                avg_slip_sell = (
                    sum(s["slippage_pct"] * s["qty"] for s in sell_slippage) / total_sell_qty
                )

                print(f"\n  {'SELL TRADES':^56}")
                print(f"  {'-'*56}")
                print(f"  Number of trades  : {len(sell_trades)}")
                print(f"  Total quantity    : {total_sell_qty:,}")
                print(f"  VWAP              : ${sell_vwap:.4f}")
                print(f"  Avg slippage      : {avg_slip_sell:+.3f}%")

        print(f"\n{'='*60}")
        print(f"  Note: Negative slippage on buys = paid less (good)")
        print(f"        Positive slippage on sells = received more (good)")
        print(f"{'='*60}\n")

    finally:
        quote_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()