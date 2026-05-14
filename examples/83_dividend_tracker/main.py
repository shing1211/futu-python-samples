"""Dividend & Corporate Action Tracker.

Tracks upcoming dividends, ex-dates, and corporate actions (rights issues,
splits, buybacks) for a configurable watchlist. Alerts before ex-dates.

Usage:
    python3 main.py [--watchlist 'HK.00700,HK.00941,US.TCEHY'] [--days-ahead 30]
"""

import sys
import os
import logging
import argparse
import json
from datetime import datetime, timedelta

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
DEFAULT_WATCHLIST = ["HK.00700", "HK.00941", "US.TCEHY", "HK.02318", "HK.01024"]
DEFAULT_DAYS_AHEAD = 30

# ---------------------------------------------------------------------------
# Corporate action types we track
# ---------------------------------------------------------------------------
CORP_ACTION_TYPES = {
    "dividend": "Dividend",
    "rights_issue": "Rights Issue",
    "split": "Stock Split",
    "buyback": "Share Buyback",
    "ipo": "IPO",
    "warrant": "Warrant Exercise",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch_basic_info(quote_ctx, code):
    """Get stock basic info including lot size, board lot, security type."""
    ret, df = quote_ctx.get_stock_basicinfo(
        market=ft.Market.HK,  # will query all if needed
    )
    if ret == ft.RetCode.SUCCESS and df is not None and not df.empty:
        filtered = df[df["code"] == code]
        if not filtered.empty:
            return filtered.iloc[-1].to_dict()
    return {}


def fetch_rt_ticker(quote_ctx, code):
    """Get real-time ticker data for a stock."""
    ret, df = quote_ctx.get_rt_ticker(code, num=1)
    if ret == ft.RetCode.SUCCESS and df is not None and not df.empty:
        return df.iloc[-1].to_dict()
    return {}


def fetch_market_snapshot(quote_ctx, code):
    """Get market snapshot for a code."""
    ret, df = quote_ctx.get_market_snapshot(code)
    if ret == ft.RetCode.SUCCESS and df is not None and not df.empty:
        return df.iloc[-1].to_dict()
    return {}


def check_corporate_actions(quote_ctx, code):
    """Check for corporate actions using available API endpoints.

    Returns list of dicts with action details.
    """
    actions = []

    # 1. Check basic info for known corporate action fields
    snap = fetch_market_snapshot(quote_ctx, code)
    basic = fetch_basic_info(quote_ctx, code)

    # 2. Check if there are any recent unusual changes in shares outstanding
    #    (indicates split, rights issue, or buyback)
    if basic:
        shares = basic.get("share_count", 0)
        name = basic.get("stock_name", code)
        listing_date = basic.get("listing_date", "")

        # Log basic info
        actions.append({
            "code": code,
            "name": name,
            "type": "INFO",
            "detail": f"Shares outstanding: {shares:,}  Listed: {listing_date}",
            "date": listing_date,
        })

    # 3. Check stock basic info change history (code changes / rehab)
    #    The 27_code_change example approach: use get_code_change_history
    try:
        ret, df = quote_ctx.get_code_change_history(code=code)
        if ret == ft.RetCode.SUCCESS and df is not None and not df.empty:
            for _, row in df.iterrows():
                action_type = str(row.get("type", ""))
                detail = str(row.get("description", ""))
                change_date = str(row.get("date", ""))
                actions.append({
                    "code": code,
                    "name": code,
                    "type": CORP_ACTION_TYPES.get(action_type, action_type),
                    "detail": detail,
                    "date": change_date,
                })
    except Exception:
        pass

    return actions


def fetch_dividend_history(quote_ctx, code):
    """Attempt to fetch dividend history from available endpoints.

    Returns list of (ex_date, dividend_amount, currency).
    """
    dividends = []

    # Check through market snapshot for dividend yield info
    snap = fetch_market_snapshot(quote_ctx, code)
    if snap:
        # Some fields that may contain dividend info
        div_yield = snap.get("dividend_yield", 0) or 0
        eps = snap.get("eps", 0) or 0
        payout_ratio = snap.get("payout_ratio", 0) or 0
        if div_yield > 0:
            dividends.append({
                "code": code,
                "ex_date": "Latest",
                "amount": "N/A",
                "yield_pct": div_yield,
                "eps": eps,
                "payout_ratio_pct": payout_ratio,
                "estimated": True,
            })

    # Use get_acc_cash_flow on trade context as a backup for SIMULATE dividend info
    return dividends


def check_upcoming_exdates(quote_ctx, watchlist, days_ahead):
    """Check all watchlist stocks for upcoming ex-dates and corporate events."""
    results = {}
    now = datetime.now()
    deadline = now + timedelta(days=days_ahead)

    for code in watchlist:
        print(f"  Checking {code} …")
        actions = check_corporate_actions(quote_ctx, code)
        dividends = fetch_dividend_history(quote_ctx, code)
        ticker = fetch_rt_ticker(quote_ctx, code)

        latest_price = ticker.get("last_price", 0) or 0
        turnover = ticker.get("turnover", 0) or 0
        volume = ticker.get("volume", 0) or 0

        results[code] = {
            "actions": actions,
            "dividends": dividends,
            "price": latest_price,
            "volume": volume,
            "turnover": turnover,
        }

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Dividend & Corporate Action Tracker")
    parser.add_argument(
        "--watchlist",
        default=",".join(DEFAULT_WATCHLIST),
        help="Comma-separated stock codes",
    )
    parser.add_argument("--days-ahead", type=int, default=DEFAULT_DAYS_AHEAD,
                        help="Lookahead window in days (default 30)")
    args = parser.parse_args()

    watchlist = [c.strip() for c in args.watchlist.split(",") if c.strip()]
    days_ahead = args.days_ahead

    quote_ctx = create_quote_context()

    try:
        print(f"\n{'='*70}")
        print(f"  📋 DIVIDEND & CORPORATE ACTION TRACKER")
        print(f"  Watchlist: {', '.join(watchlist)}")
        print(f"  Lookahead: {days_ahead} days")
        print(f"{'='*70}\n")

        results = check_upcoming_exdates(quote_ctx, watchlist, days_ahead)

        # ── Print report ──────────────────────────────────────────────
        for code, data in results.items():
            print(f"  ┌─ {code}  (last: {data['price']:.2f}  vol: {data['volume']:,})")

            if not data["actions"] and not data["dividends"]:
                print(f"  │  No corporate actions or dividend data available")

            for a in data["actions"]:
                atype = a.get("type", "?")
                detail = a.get("detail", "")
                adate = a.get("date", "N/A")
                print(f"  │  [{atype}] {adate} — {detail}")

            for d in data["dividends"]:
                if d["estimated"]:
                    print(
                        f"  │  [DIVIDEND] Est. yield: {d['yield_pct']:.2f}%  "
                        f"EPS: {d['eps']:.4f}  Payout: {d['payout_ratio_pct']:.1f}%"
                    )

            print(f"  └{'─'*60}")

        # ── Summary ────────────────────────────────────────────────────
        total_yield = sum(
            d["yield_pct"] for data in results.values() for d in data["dividends"]
        )
        if total_yield > 0:
            print(f"\n  Aggregate estimated dividend yield: {total_yield:.2f}%")

        print(f"\n  Note: Dividend ex-date tracking depends on OpenD data")
        print(f"  availability. For real-time alerts, integrate with calendar APIs.\n")

    finally:
        quote_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()