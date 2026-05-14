"""Options Volatility Skew Scanner.

Scans option chains to compute implied volatility skew across strikes
and expiries. Identifies mispriced options and displays the vol surface
as a formatted table.

Usage:
    python3 main.py [--stock HK.00700] [--min-oi 50]
"""

import sys
import os
import logging
import argparse
import math
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

DEFAULT_STOCK = "HK.00700"
DEFAULT_MIN_OI = 50


def norm_cdf(x):
    """Standard normal CDF via math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def implied_vol_newton(market_price, S, K, T, r, option_type, max_iter=100):
    """Solve for implied vol using Newton-Raphson.

    Returns implied vol or None if no convergence.
    """
    if T <= 0 or S <= 0 or K <= 0 or market_price <= 0:
        return None

    sigma = 0.3  # initial guess
    for _ in range(max_iter):
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)

        if option_type == "call":
            model_price = S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
        else:
            model_price = K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)

        # Vega
        vega = S * math.exp(-d1 ** 2 / 2) * math.sqrt(T) / math.sqrt(2 * math.pi)

        diff = model_price - market_price
        if abs(vega) < 1e-12:
            break

        sigma -= diff / vega
        sigma = max(0.001, min(sigma, 3.0))

        if abs(diff) < 0.001:
            return sigma

    return sigma if abs(diff) < 0.1 else None


def classify_option(name, code):
    """Classify as CALL or PUT from name/code."""
    upper = (name + " " + code).upper()
    if "CALL" in upper:
        return "CALL"
    elif "PUT" in upper:
        return "PUT"
    elif code[-1] in "Cc":
        return "CALL"
    elif code[-1] in "Pp":
        return "PUT"
    return "UNKNOWN"


def fetch_all_options(quote_ctx, stock, num=50):
    """Fetch all option contracts with pagination."""
    contracts = []
    start = ""
    for _ in range(10):
        ret, df, next_page = quote_ctx.get_option_chain(
            code=stock, num=num, start=start,
        )
        if ret != ft.RetCode.SUCCESS:
            break
        if df is not None and not df.empty:
            contracts.extend(df.to_dict("records"))
        if not next_page:
            break
        start = next_page
    return contracts


def get_spot(quote_ctx, stock):
    """Get spot price."""
    ret, df = quote_ctx.get_stock_quote(stock)
    if ret == ft.RetCode.SUCCESS and df is not None and not df.empty:
        return float(df.iloc[-1]["last_price"])
    return None


def moneyness_label(strike, spot):
    """Classify strike relative to spot."""
    ratio = strike / spot
    if abs(ratio - 1.0) < 0.02:
        return "ATM"
    elif ratio < 0.95:
        return "Deep-OTM" if ratio < 0.90 else "OTM"
    elif ratio > 1.05:
        return "Deep-ITM" if ratio > 1.10 else "ITM"
    return "Near-ATM"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Options Volatility Skew Scanner")
    parser.add_argument("--stock", default=DEFAULT_STOCK, help="Underlying stock")
    parser.add_argument("--min-oi", type=int, default=DEFAULT_MIN_OI,
                        help="Minimum open interest to include")
    args = parser.parse_args()

    stock = args.stock
    min_oi = args.min_oi
    risk_free = 0.05

    quote_ctx = create_quote_context()

    try:
        spot = get_spot(quote_ctx, stock)
        if spot is None:
            logger.error("Cannot get spot for %s", stock)
            return
        logger.info("Spot price for %s: %.2f", stock, spot)

        contracts = fetch_all_options(quote_ctx, stock)
        if not contracts:
            logger.warning("No options found for %s", stock)
            return
        logger.info("Found %d contracts", len(contracts))

        # ── Compute IV for each contract ───────────────────────────────
        results = []
        for c in contracts:
            code = str(c.get("code", ""))
            name = str(c.get("stock_name", ""))
            last = float(c.get("last_price", 0) or 0)
            oi = float(c.get("open_interest", 0) or 0)
            volume = float(c.get("volume", 0) or 0)
            strike = float(c.get("exercise_price", 0) or 0)
            expiry_str = str(c.get("end_date", ""))

            if last <= 0 or oi < min_oi:
                continue

            opt_type = classify_option(name, code)
            if opt_type == "UNKNOWN":
                continue

            # Estimate expiry (try parsing end_date)
            days_to_expiry = 30  # default fallback
            try:
                exp_date = datetime.strptime(expiry_str, "%Y-%m-%d")
                days_to_expiry = max(1, (exp_date - datetime.now()).days)
            except (ValueError, TypeError):
                pass

            T = days_to_expiry / 365.0
            iv = implied_vol_newton(last, spot, strike, T, risk_free, opt_type.lower())

            if iv is None:
                continue

            iv_pct = iv * 100
            mon = moneyness_label(strike, spot)

            results.append({
                "code": code,
                "type": opt_type,
                "strike": strike,
                "expiry": expiry_str[:10] if expiry_str else "N/A",
                "days": days_to_expiry,
                "last": last,
                "oi": int(oi),
                "volume": int(volume),
                "iv_pct": iv_pct,
                "moneyness": mon,
            })

        if not results:
            print("No contracts with sufficient data to compute IV.")
            return

        # ── Group by expiry for skew table ─────────────────────────────
        by_expiry = defaultdict(list)
        for r in results:
            by_expiry[r["expiry"]].append(r)

        print(f"\n{'='*80}")
        print(f"  📈 OPTIONS VOLATILITY SKEW — {stock}  (spot {spot:.2f})")
        print(f"{'='*80}\n")

        # Print per-expiry tables
        for expiry in sorted(by_expiry.keys()):
            items = sorted(by_expiry[expiry], key=lambda x: x["strike"])
            if not items:
                continue

            # Find min IV (this is the "smile" bottom)
            min_iv = min(r["iv_pct"] for r in items)

            print(f"  Expiry: {expiry}  ({items[0]['days']} DTE)")
            print(f"  {'Code':<12} {'Type':<6} {'Strike':>8} {'Moneyness':<10} "
                  f"{'Last':>8} {'OI':>8} {'Vol':>6} {'IV%':>7}")
            print(f"  {'-'*12} {'-'*6} {'-'*8} {'-'*10} {'-'*8} {'-'*8} {'-'*6} {'-'*7}")

            for r in items:
                # Visual indicator for lowest IV (vol smile bottom)
                marker = " ◂" if abs(r["iv_pct"] - min_iv) < 0.5 else ""
                print(
                    f"  {r['code']:<12} {r['type']:<6} {r['strike']:>8.2f} "
                    f"{r['moneyness']:<10} {r['last']:>8.4f} {r['oi']:>8,} "
                    f"{r['volume']:>6,} {r['iv_pct']:>6.1f}%{marker}"
                )

            # Skew summary
            call_ivs = [r["iv_pct"] for r in items if r["type"] == "CALL"]
            put_ivs = [r["iv_pct"] for r in items if r["type"] == "PUT"]
            if call_ivs and put_ivs:
                skew = max(call_ivs) - min(put_ivs)
                print(f"  Skew range: {min(put_ivs):.1f}% – {max(call_ivs):.1f}% "
                      f"(spread: {skew:.1f}pp)")
            print()

        # ── Overall summary ────────────────────────────────────────────
        all_ivs = [r["iv_pct"] for r in results]
        atm_candidates = [r for r in results if r["moneyness"] in ("ATM", "Near-ATM")]
        if atm_candidates:
            atm_iv = statistics.mean([r["iv_pct"] for r in atm_candidates])
            print(f"  📊 ATM average IV: {atm_iv:.1f}%")

        print(f"  IV range: {min(all_ivs):.1f}% – {max(all_ivs):.1f}%")
        print(f"  Contracts with IV computed: {len(results)}")
        print(f"{'='*80}\n")

    finally:
        quote_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()