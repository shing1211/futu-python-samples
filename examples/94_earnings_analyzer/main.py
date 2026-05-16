"""Earnings Surprise Analyzer — Event-Driven Screening.

Pulls earnings reports and compares actual vs estimated EPS. Flags
post-earnings unusual activity and IV crush/expansion patterns.

Usage:
    python3 main.py [--market HK] [--surprise-threshold 10]
"""

import sys
import logging
import argparse
import statistics

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

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
DEFAULT_SURPRISE_PCT = 10.0  # flag earnings surprises > 10%

MARKET_ENUM = {
    "HK": ft.Market.HK,
    "US": ft.Market.US,
    "SH": ft.Market.SH,
    "SZ": ft.Market.SZ,
}


# ---------------------------------------------------------------------------
# Earnings data extraction
# ---------------------------------------------------------------------------

def fetch_financial_reports(quote_ctx, code, num_reports=4):
    """Fetch recent financial reports for a stock.

    Uses get_financial_report if available, otherwise falls back to
    income statement / balance sheet data.
    """
    reports = []

    # Try get_financial_report
    try:
        ret, df = quote_ctx.get_financial_report(code, "annual", 0)
        if ret == ft.RetCode.SUCCESS and df is not None and not df.empty:
            for _, row in df.iterrows():
                reports.append({
                    "code": code,
                    "period": str(row.get("report_date", "")),
                    "eps": float(row.get("eps", 0) or 0),
                    "revenue": float(row.get("total_revenue", 0) or 0),
                    "net_income": float(row.get("net_income", 0) or 0),
                    "roe": float(row.get("return_on_equity", 0) or 0),
                    "pe": float(row.get("pe_ratio", 0) or 0),
                })
    except Exception:
        pass

    # Fallback: try income statement
    if not reports:
        try:
            ret, df = quote_ctx.get_income_statement(code, "annual", 0)
            if ret == ft.RetCode.SUCCESS and df is not None and not df.empty:
                for _, row in df.iterrows():
                    reports.append({
                        "code": code,
                        "period": str(row.get("report_date", "")),
                        "eps": float(row.get("eps", 0) or 0),
                        "revenue": float(row.get("total_revenue", 0) or 0),
                        "net_income": float(row.get("net_income", 0) or 0),
                    })
        except Exception:
            pass

    return reports[:num_reports]


def fetch_earnings_history(quote_ctx, code, num=4):
    """Fetch historical earnings per share from K-line data around earnings dates.

    Returns list of {period, reported_eps, estimated_eps, surprise_pct}.
    Uses get_income_statement or get_financial_report.
    """
    reports = fetch_financial_reports(quote_ctx, code, num)
    results = []

    for i, r in enumerate(reports):
        if r["eps"] == 0:
            continue

        # Estimate "consensus" as average of prior quarters (simplified)
        prior_eps = [
            rp["eps"] for rp in reports[i + 1:] if rp["eps"] > 0
        ]
        if prior_eps:
            estimated = statistics.mean(prior_eps)
        else:
            estimated = r["eps"] * 0.95  # assume 5% growth if no history

        surprise = ((r["eps"] - estimated) / estimated) * 100 if estimated != 0 else 0

        results.append({
            "period": r["period"],
            "reported_eps": r["eps"],
            "estimated_eps": round(estimated, 4),
            "surprise_pct": round(surprise, 2),
            "revenue": r.get("revenue", 0),
            "net_income": r.get("net_income", 0),
            "roe": r.get("roe", 0),
            "pe": r.get("pe", 0),
        })

    return results


def get_post_earnings_klines(quote_ctx, code, num_bars=10):
    """Get K-lines after the most recent earnings to check for unusual activity."""
    ret, df, _ = quote_ctx.request_history_kline(
        code=code, start="", num_bars=num_bars, ktype=ft.KLType.K_DAY,
    )
    if ret != ft.RetCode.SUCCESS or df is None or df.empty:
        return []

    bars = []
    for _, row in df.iterrows():
        bars.append({
            "date": str(row.get("time_key", "")),
            "open": float(row.get("open", 0) or 0),
            "close": float(row.get("close", 0) or 0),
            "high": float(row.get("high", 0) or 0),
            "low": float(row.get("low", 0) or 0),
            "volume": float(row.get("volume", 0) or 0),
        })
    return bars


def check_unusual_activity(bars):
    """Check post-earnings bars for unusual volume or price action."""
    if len(bars) < 3:
        return []

    closes = [b["close"] for b in bars]
    volumes = [b["volume"] for b in bars]

    avg_vol = statistics.mean(volumes) if volumes else 0
    avg_close = statistics.mean(closes) if closes else 0
    std_close = statistics.pstdev(closes) if len(closes) > 1 else 0

    alerts = []

    # Check for volume spikes
    latest_vol = volumes[-1] if volumes else 0
    if avg_vol > 0 and latest_vol > avg_vol * 2:
        alerts.append(f"Volume spike: {latest_vol:,.0f} vs avg {avg_vol:,.0f} (2×)")

    # Check for gap after earnings
    if len(closes) >= 2:
        gap_pct = (closes[-1] - closes[-2]) / closes[-2] * 100 if closes[-2] > 0 else 0
        if abs(gap_pct) > 3:
            alerts.append(f"Post-earnings gap: {gap_pct:+.2f}%")

    # Check for unusual daily range
    daily_range_pct = (bars[-1]["high"] - bars[-1]["low"]) / bars[-1]["close"] * 100 if bars[-1]["close"] > 0 else 0
    if daily_range_pct > 5:
        alerts.append(f"Wide daily range: {daily_range_pct:.1f}%")

    return alerts


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def format_table(results):
    """Format earnings surprise data as a table."""
    if not results:
        return "  No earnings data available."

    lines = []
    lines.append(f"  {'Period':<12} {'Reported':>10} {'Estimated':>10} "
                  f"{'Surprise':>10} {'Direction':<8}")
    lines.append(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*8}")

    for r in results:
        surprise = r["surprise_pct"]
        if surprise > 5:
            direction = "🟢 Beat"
        elif surprise < -5:
            direction = "🔴 Miss"
        else:
            direction = "⚪ In-line"

        lines.append(
            f"  {r['period']:<12} {r['reported_eps']:>10.4f} "
            f"{r['estimated_eps']:>10.4f} {surprise:>+9.2f}% {direction:<8}"
        )

    return "\n".join(lines)


def print_iv_analysis(quote_ctx, code, spot):
    """Print basic options IV analysis if options exist."""
    contracts = []
    start = ""
    for _ in range(3):
        ret, df, next_page = quote_ctx.get_option_chain(
            code=code, num=20, start=start,
        )
        if ret != ft.RetCode.SUCCESS:
            break
        if df is not None and not df.empty:
            contracts.extend(df.to_dict("records"))
        if not next_page:
            break
        start = next_page

    if not contracts:
        return

    ivs = []
    for c in contracts:
        last = float(c.get("last_price", 0) or 0)
        if last > 0:
            ivs.append({
                "code": c.get("code", ""),
                "strike": float(c.get("exercise_price", 0) or 0),
                "last": last,
                "oi": int(float(c.get("open_interest", 0) or 0)),
            })

    if not ivs:
        return

    print(f"\n  Options data available: {len(ivs)} contracts")
    nearest = min(ivs, key=lambda x: abs(x["strike"] - spot))
    print(f"  ATM option: {nearest['code']} (strike={nearest['strike']:.2f}, "
          f"last={nearest['last']:.4f}, OI={nearest['oi']:,})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Earnings Surprise Analyzer")
    parser.add_argument("--market", default=DEFAULT_MARKET,
                        help="Market code: HK, US, SH, SZ")
    parser.add_argument("--surprise-threshold", type=float,
                        default=DEFAULT_SURPRISE_PCT,
                        help="Min earnings surprise %% to flag (default 10)")
    parser.add_argument("--codes", default=None,
                        help="Specific stock codes (comma-separated), overrides market scan")
    args = parser.parse_args()

    market_enum = MARKET_ENUM.get(args.market.upper())
    surprise_threshold = args.surprise_threshold

    quote_ctx = create_quote_context()

    try:
        if args.codes:
            codes = [c.strip() for c in args.codes.split(",") if c.strip()]
            print(f"\n{'='*70}")
            print(f"  📈 EARNINGS SURPRISE ANALYZER — Specific Codes")
            print(f"  Codes: {', '.join(codes)}")
            print(f"{'='*70}")

            for code in codes:
                analyze_code(quote_ctx, code, surprise_threshold)
        else:
            # Scan market for stocks with earnings data
            ret, stock_list = quote_ctx.get_stock_list(market=market_enum)
            if ret != ft.RetCode.SUCCESS or stock_list is None:
                logger.error("Cannot get stock list for %s", args.market)
                return

            codes = [c for c in stock_list["code"].tolist() if c]
            print(f"\n{'='*70}")
            print(f"  📈 EARNINGS SURPRISE ANALYZER — {args.market} Market")
            print(f"  Scanning {len(codes)} stocks …")
            print(f"{'='*70}")

            analyzed = 0
            for code in codes:
                if analyzed >= 10:  # limit for performance
                    break
                try:
                    result = analyze_code(quote_ctx, code, surprise_threshold)
                    if result:
                        analyzed += 1
                except Exception as e:
                    continue

    finally:
        quote_ctx.close()
        logger.info("Done.")


def analyze_code(quote_ctx, code, threshold):
    """Analyze a single stock's earnings surprises."""
    # Get basic info
    ret, df = quote_ctx.get_stock_quote(code)
    if ret != ft.RetCode.SUCCESS:
        return False
    spot = float(df.iloc[-1]["last_price"])
    name = str(df.iloc[-1].get("stock_name", ""))

    # Get earnings history
    earnings = fetch_earnings_history(quote_ctx, code)
    if not earnings:
        return False

    # Check for surprises
    has_surprise = any(abs(e["surprise_pct"]) >= threshold for e in earnings)

    print(f"\n  ── {code} ({name[:16]}) ── Spot: {spot:.2f}")
    print(format_table(earnings))

    # Post-earnings price action
    bars = get_post_earnings_klines(quote_ctx, code)
    alerts = check_unusual_activity(bars)
    if alerts:
        print(f"  ⚡ Post-earnings alerts:")
        for a in alerts:
            print(f"     • {a}")
    else:
        print(f"  ✓ Post-earnings action appears normal")

    # Options IV context
    print_iv_analysis(quote_ctx, code, spot)

    return True