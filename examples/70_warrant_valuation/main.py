"""Warrant Valuation Dashboard — Analytics only (no trading).

Pulls all warrants for a given underlying via get_warrant(), computes intrinsic
value, time value, and a simplified BSM implied vol estimate. Ranks by
perceived mispricing.

Usage:
    python3 main.py <underlying_code>
"""

import sys
import os
import logging
import math
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connect import create_quote_context, clear_connection_cache
import futu as ft

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DEFAULT_UNDERLYING = "HK.00700"

# ---------------------------------------------------------------------------
# Black-Scholes (same approach as 58_options_greeks/greeks.py)
# ---------------------------------------------------------------------------

def norm_cdf(x):
    """Standard normal CDF via math.erf (Abramowitz & Stegun)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def black_scholes_price(S, K, T, r, sigma, option_type):
    """BSM European option price.  Returns float or None on bad input."""
    if T <= 0 or sigma <= 0 or S <= 0:
        return None
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if option_type == "call":
        return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    else:
        return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch_warrants(quote_ctx, underlying):
    """Return warrant rows as a list of dicts.  Handles pagination."""
    all_rows = []
    has_more = True
    start = 0
    while has_more:
        ret, df, has_more = quote_ctx.get_warrant(
            underlying_code=underlying,
            start=start,
        )
        if ret != ft.RetCode.SUCCESS:
            logger.error("get_warrant failed: %s", ret)
            break
        if df is not None and not df.empty:
            all_rows.extend(df.to_dict("records"))
            start += len(df)
        else:
            break
    return all_rows


def is_call(name):
    """Heuristic: warrant name contains 'CALL' or 'C' near the end."""
    upper = name.upper()
    return "CALL" in upper or upper.endswith("C")


def is_put(name):
    """Heuristic: warrant name contains 'PUT' or 'P' near the end."""
    upper = name.upper()
    return "PUT" in upper or upper.endswith("P")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Warrant valuation dashboard")
    parser.add_argument("underlying", nargs="?", default=DEFAULT_UNDERLYING,
                        help="Underlying stock code")
    parser.add_argument("--risk-free", type=float, default=0.05,
                        help="Risk-free rate (default 0.05)")
    args = parser.parse_args()

    underlying = args.underlying
    risk_free = args.risk_free

    quote_ctx = create_quote_context()

    try:
        # ── Underlying spot price ──────────────────────────────────────
        ret, df = quote_ctx.get_stock_quote(underlying)
        if ret != ft.RetCode.SUCCESS:
            logger.error("Cannot fetch quote for %s", underlying)
            return
        spot = df.iloc[-1]["last_price"]
        logger.info("Underlying %s spot price: %.2f", underlying, spot)

        # ── Fetch warrants ─────────────────────────────────────────────
        warrants = fetch_warrants(quote_ctx, underlying)
        if not warrants:
            logger.warning("No warrants found for %s", underlying)
            return
        logger.info("Found %d warrant(s) for %s", len(warrants), underlying)

        # ── Compute valuation for each warrant ─────────────────────────
        today = date.today()
        results = []

        for w in warrants:
            code = w.get("stock_code", "")
            name = w.get("stock_name", "")
            last_price = float(w.get("last_price", 0) or 0)
            if last_price <= 0:
                continue

            # Extract strike — SDK field name varies; try common names
            strike = float(w.get("exercise_price", 0) or
                           w.get("strike_price", 0) or
                           w.get("conversion_price", 0) or 0)
            if strike <= 0:
                continue

            # Expiry
            expiry_str = w.get("end_date", "") or w.get("maturity_date", "")
            if expiry_str:
                try:
                    expiry = datetime.strptime(str(expiry_str), "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    expiry = None
            else:
                expiry = None

            if expiry is None or expiry <= today:
                continue

            days = (expiry - today).days
            T = days / 365.0

            # Determine warrant type
            wtype = "call" if is_call(name) else ("put" if is_put(name) else "call")

            # Intrinsic value
            if wtype == "call":
                intrinsic = max(0, spot - strike)
            else:
                intrinsic = max(0, strike - spot)

            time_value = last_price - intrinsic
            if time_value < 0:
                time_value = 0

            # Simplified implied vol (back out from BSM)
            # Newton-Raphson on sigma
            target = last_price
            sigma = 0.5  # initial guess
            for _ in range(50):
                price = black_scholes_price(spot, strike, T, risk_free, sigma, wtype)
                if price is None:
                    break
                vega_num = black_scholes_price(spot, strike, T, risk_free, sigma + 1e-5, wtype)
                if vega_num is None:
                    break
                vega = (vega_num - price) / 1e-5
                if abs(vega) < 1e-12:
                    break
                sigma -= (price - target) / vega
                sigma = max(0.001, min(sigma, 5.0))  # clamp

            # Mispricing score: |market - BSM_theoretical| / market
            theoretical = black_scholes_price(spot, strike, T, risk_free, sigma, wtype)
            if theoretical and theoretical > 0:
                misprice = abs(last_price - theoretical) / last_price
            else:
                misprice = None

            results.append({
                "code": code,
                "name": name[:20],
                "strike": strike,
                "expiry": expiry.isoformat(),
                "days": days,
                "spot": spot,
                "last": last_price,
                "intrinsic": round(intrinsic, 4),
                "time_val": round(time_value, 4),
                "iv": round(sigma * 100, 2),
                "misprice": round(misprice * 100, 2) if misprice is not None else None,
                "type": wtype.upper(),
            })

        # ── Sort by mispricing (most mispriced first) ───────────────────
        results.sort(key=lambda r: r["misprice"] if r["misprice"] is not None else -1,
                      reverse=True)

        # ── Display ────────────────────────────────────────────────────
        header = (
            f"{'Code':<10} {'Type':<5} {'Strike':>8} {'Expiry':>10} {'Days':>5} "
            f"{'Last':>8} {'Intr':>8} {'TimeV':>8} {'IV%':>7} {'Mis%':>7}"
        )
        print("\n" + "=" * len(header))
        print(f"  WARRANT VALUATION — {underlying}  (spot {spot:.2f})")
        print("=" * len(header))
        print(header)
        print("-" * len(header))

        for r in results[:30]:  # top 30
            mis = f"{r['misprice']:.1f}%" if r['misprice'] is not None else "  N/A"
            print(
                f"{r['code']:<10} {r['type']:<5} {r['strike']:>8.2f} "
                f"{r['expiry']:>10} {r['days']:>5} "
                f"{r['last']:>8.4f} {r['intrinsic']:>8.4f} "
                f"{r['time_val']:>8.4f} {r['iv']:>6.1f}% {mis:>7}"
            )

        print("-" * len(header))
        print(f"  {len(results)} warrant(s) analysed. Top mispricings shown first.\n")

    finally:
        quote_ctx.close()


if __name__ == "__main__":
    main()