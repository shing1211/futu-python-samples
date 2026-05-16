"""Futures Term Structure & Roll Yield — Dynamic discovery.

Dynamically discovers active futures contracts for an underlying,
builds the term structure, computes roll yield, and classifies contango/backwardation.

Usage:
    python3 main.py HK.HHI     # Hang Seng Index Futures
"""

import sys
import logging
import argparse
from datetime import datetime, timedelta
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

DEFAULT_FUTURE_STEM = "HK.HHI"


def discover_futures(quote_ctx, stem, months_ahead=12):
    """Dynamically discover active futures contracts.

    Attempts month-by-month codes in the format STEM_YYYYMM.
    Falls back to get_market_snapshot filtering if that fails.
    """
    now = datetime.now()
    contracts = []

    for offset in range(months_ahead):
        target = now + timedelta(days=offset * 30)
        # Try standard futures naming: STEM_YYYYMM
        month_code = target.strftime("%Y%m")
        code = f"{stem}_{month_code}"
        ret, snapshot = quote_ctx.get_market_snapshot(code)
        if ret == ft.RetCode.SUCCESS and snapshot is not None and not snapshot.empty:
            contracts.append({
                "code": code,
                "last_price": float(snapshot.iloc[-1].get("last_price", 0) or 0),
                "volume": float(snapshot.iloc[-1].get("volume", 0) or 0),
                "turnover": float(snapshot.iloc[-1].get("turnover", 0) or 0),
            })

    # Fallback: try querying all futures of the exchange
    if not contracts:
        logger.warning("Standard naming failed, trying snapshot scan …")
        candidates = [
            f"{stem}_{(now + timedelta(days=d)).strftime('%Y%m')}"
            for d in range(0, months_ahead * 30, 30)
        ]
        ret, snapshot = quote_ctx.get_market_snapshot(candidates)
        if ret == ft.RetCode.SUCCESS and snapshot is not None and not snapshot.empty:
            for _, row in snapshot.iterrows():
                code = row.get("code", "")
                last = float(row.get("last_price", 0) or 0)
                if last > 0:
                    contracts.append({
                        "code": code,
                        "last_price": last,
                        "volume": float(row.get("volume", 0) or 0),
                        "turnover": float(row.get("turnover", 0) or 0),
                    })

    return contracts


def parse_expiry_from_code(code, stem):
    """Try to extract expiry year-month from futures code."""
    suffix = code.replace(stem, "").lstrip("_")
    try:
        return datetime.strptime(suffix, "%Y%m")
    except (ValueError, TypeError):
        return None


def compute_roll_yield(near_price, far_price, near_expiry, far_expiry):
    """Annualised roll yield.  Returns (yield_pct, days_to_expiry_diff)."""
    if near_price <= 0 or far_price <= 0:
        return None, None
    days_diff = (far_expiry - near_expiry).days
    if days_diff <= 0:
        return None, None
    roll_yield = (far_price - near_price) / near_price
    annualised = roll_yield * (365.0 / days_diff)
    return annualised, days_diff


def find_expiry(quote_ctx, code):
    """Attempt to find expiry date via get_instrument_info or last_trade_time."""
    ret, info = quote_ctx.get_instrument_info(code)
    if ret == ft.RetCode.SUCCESS and info is not None and not info.empty:
        # Try common expiry columns
        for col in ["end_date", "maturity_date", "expiry_date", "last_trade_time"]:
            if col in info.columns:
                val = info.iloc[-1].get(col, "")
                if val:
                    try:
                        return datetime.strptime(str(val), "%Y-%m-%d")
                    except ValueError:
                        pass
    return None


def term_structure_ascii(contracts, now):
    """Render term structure as ASCII chart."""
    if not contracts:
        print("  [no contracts found]")
        return

    prices = [c["last_price"] for c in contracts]
    min_p = min(prices) if prices else 0
    max_p = max(prices) if prices else 1
    span = max_p - min_p if max_p > min_p else 1

    chart_w = 50
    print(f"\n  {'Code':<18} {'Price':>10} {'Vol':>8} {'Days':>5} {'Chart'}")
    print(f"  {'-'*18} {'-'*10} {'-'*8} {'-'*5} {'-'*chart_w}")
    for c in sorted(contracts, key=lambda x: x["code"]):
        expiry = parse_expiry_from_code(c["code"],
                  c["code"].rsplit("_", 1)[0] if "_" in c["code"] else "")
        days = (expiry - now).days if expiry else 0
        bar_len = int((c["last_price"] - min_p) / span * chart_w) if span > 0 else 0
        bar = "█" * max(1, bar_len)
        print(f"  {c['code']:<18} {c['last_price']:>10.2f} "
              f"{c['volume']:>8,.0f} {days:>5}  {bar}")


def classify_term_structure(contracts):
    """Classify as contango, backwardation, or humped."""
    if len(contracts) < 2:
        return "INSUFFICIENT_DATA"

    sorted_c = sorted(contracts, key=lambda x: x["code"])
    prices = [c["last_price"] for c in sorted_c]

    strictly_increasing = all(prices[i] < prices[i + 1] for i in range(len(prices) - 1))
    strictly_decreasing = all(prices[i] > prices[i + 1] for i in range(len(prices) - 1))

    if strictly_increasing:
        return "CONTANGO (normal)"
    elif strictly_decreasing:
        return "BACKWARDATION (inverted)"
    else:
        # Check if humped (rising then falling)
        peak_idx = prices.index(max(prices))
        if 0 < peak_idx < len(prices) - 1:
            return "HUMPED"
        return "IRREGULAR"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Futures term structure & roll yield")
    parser.add_argument("stem", nargs="?", default=DEFAULT_FUTURE_STEM,
                        help="Futures code stem (e.g. HK.HHI)")
    args = parser.parse_args()

    stem = args.stem
    now = datetime.now()

    quote_ctx = create_quote_context()

    try:
        # ── Discover contracts ─────────────────────────────────────────
        logger.info("Discovering futures contracts for %s …", stem)
        contracts = discover_futures(quote_ctx, stem)
        if not contracts:
            logger.warning("No active futures found for stem %s", stem)
            logger.info("Try: HK.HHI (Hang Seng), HK.MHI (MHI), US.ESM (S&P e-mini)")
            return

        logger.info("Found %d active contract(s)", len(contracts))

        # ── Attempt to enrich with instrument info (dynamic discovery) ──
        for c in contracts:
            expiry = find_expiry(quote_ctx, c["code"])
            if expiry:
                c["expiry"] = expiry
            else:
                parsed = parse_expiry_from_code(c["code"], stem)
                if parsed:
                    c["expiry"] = parsed

        # ── Term structure ─────────────────────────────────────────────
        term = classify_term_structure(contracts)
        print(f"\n{'='*64}")
        print(f"  FUTURES TERM STRUCTURE — {stem}")
        print(f"  {len(contracts)} active contracts  |  Market state: {term}")
        print(f"{'='*64}")

        term_structure_ascii(contracts, now)

        # ── Roll yield ─────────────────────────────────────────────────
        sorted_c = sorted(contracts, key=lambda x: x["code"])
        print(f"\n  {'Pair':<38} {'Roll Yield':>12} {'Ann. Yield':>12} {'Days':>6}")
        print(f"  {'-'*38} {'-'*12} {'-'*12} {'-'*6}")

        for i in range(len(sorted_c) - 1):
            near = sorted_c[i]
            far = sorted_c[i + 1]
            near_exp = near.get("expiry")
            far_exp = far.get("expiry")
            if near_exp is None or far_exp is None:
                continue
            ry, days = compute_roll_yield(
                near["last_price"], far["last_price"], near_exp, far_exp,
            )
            if ry is not None:
                pair_label = f"{near['code']} → {far['code']}"
                print(f"  {pair_label:<38} {ry:>11.4%} {ry*100:>11.2f}% {days:>5}")

        print()

    finally:
        quote_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()