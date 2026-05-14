"""Options Calendar Spread Builder — SIMULATE only.

Constructs calendar spreads (same strike, different expiry) by finding
options with theoretical edge from time decay differential.

Usage:
    python3 main.py [--stock HK.00700] [--strike-offset 0.0] [--max-minutes 10]
"""

import sys
import os
import logging
import argparse
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connect import (
    create_quote_context,
    create_trade_context,
    get_demo_trade_password,
    clear_connection_cache,
)
import futu as ft

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DEFAULT_STOCK = "HK.00700"


def norm_cdf(x):
    """Standard normal CDF via math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_price(S, K, T, r, sigma, opt_type):
    """Black-Scholes price. Returns float or None."""
    if T <= 0 or sigma <= 0 or S <= 0:
        return None
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if opt_type == "call":
        return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    else:
        return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)


def implied_vol(price, S, K, T, r, opt_type, max_iter=100):
    """Newton-Raphson implied volatility solver."""
    if T <= 0 or price <= 0:
        return None
    sigma = 0.3
    for _ in range(max_iter):
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        if opt_type == "call":
            model = S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
        else:
            model = K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)
        vega = S * math.exp(-d1 ** 2 / 2) * math.sqrt(T) / math.sqrt(2 * math.pi)
        diff = model - price
        if abs(vega) < 1e-12:
            break
        sigma -= diff / vega
        sigma = max(0.001, min(sigma, 5.0))
        if abs(diff) < 0.01:
            return sigma
    return sigma


def classify_option(name, code):
    upper = (name + " " + code).upper()
    if "CALL" in upper or (code and code[-1] in "Cc"):
        return "call"
    elif "PUT" in upper or (code and code[-1] in "Pp"):
        return "put"
    return "call"  # default


def fetch_option_chain(quote_ctx, stock, num=100):
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


def find_calendar_opportunities(quote_ctx, stock, spot):
    """Find calendar spread opportunities.

    Groups options by strike and type, finds pairs with different expiries.
    Returns sorted list by theoretical edge (annualised).
    """
    contracts = fetch_option_chain(quote_ctx, stock)
    if not contracts:
        return []

    risk_free = 0.05

    # Group by (strike, option_type)
    groups = {}
    for c in contracts:
        code = str(c.get("code", ""))
        name = str(c.get("stock_name", ""))
        last = float(c.get("last_price", 0) or 0)
        volume = float(c.get("volume", 0) or 0)
        oi = float(c.get("open_interest", 0) or 0)
        strike = float(c.get("exercise_price", 0) or 0)
        expiry_str = str(c.get("end_date", ""))
        opt_type = classify_option(name, code)
        moneyness = abs(strike / spot - 1)

        if last <= 0 or oi <= 0:
            continue

        # Parse expiry
        days_to_exp = 30
        try:
            exp_date = __import__("datetime").datetime.strptime(expiry_str, "%Y-%m-%d")
            days_to_exp = max(1, (exp_date - __import__("datetime").datetime.now()).days)
        except (ValueError, TypeError):
            pass

        key = (strike, opt_type)
        if key not in groups:
            groups[key] = []
        groups[key].append({
            "code": code,
            "name": name,
            "strike": strike,
            "expiry": expiry_str[:10],
            "days": days_to_exp,
            "last": last,
            "volume": int(volume),
            "oi": int(oi),
            "moneyness": moneyness,
            "type": opt_type,
            "iv": implied_vol(last, spot, strike, days_to_exp / 365, risk_free, opt_type),
        })

    opportunities = []

    for (strike, opt_type), items in groups.items():
        if len(items) < 2:
            continue

        # Sort by expiry (near to far)
        items.sort(key=lambda x: x["days"])

        # Compare each pair
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                near = items[i]
                far = items[j]

                # Calendar spread: sell near, buy far
                if near["iv"] is None or far["iv"] is None:
                    continue

                # Theoretical edge: vol differential vs time decay differential
                vol_spread = far["iv"] - near["iv"]  # positive = near is cheaper vol
                time_ratio = near["days"] / max(far["days"], 1)

                # Annualised edge estimate
                if near["days"] > 0:
                    annualised_edge = vol_spread * (365 / near["days"]) ** 0.5
                else:
                    annualised_edge = 0

                opportunities.append({
                    "strike": strike,
                    "type": opt_type.upper(),
                    "near_code": near["code"],
                    "near_expiry": near["expiry"],
                    "near_days": near["days"],
                    "near_iv": near["iv"] * 100 if near["iv"] else 0,
                    "near_price": near["last"],
                    "near_oi": near["oi"],
                    "far_code": far["code"],
                    "far_expiry": far["expiry"],
                    "far_days": far["days"],
                    "far_iv": far["iv"] * 100 if far["iv"] else 0,
                    "far_price": far["last"],
                    "far_oi": far["oi"],
                    "vol_spread": vol_spread * 100,
                    "annualised_edge": annualised_edge,
                    "moneyness": near["moneyness"],
                })

    opportunities.sort(key=lambda x: abs(x["vol_spread"]), reverse=True)
    return opportunities


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Options Calendar Spread Builder (SIMULATE)")
    parser.add_argument("--stock", default=DEFAULT_STOCK, help="Underlying stock")
    parser.add_argument("--strike-offset", type=float, default=0.0,
                        help="Strike offset from ATM (as fraction, e.g. 0.02 for 2%%)")
    parser.add_argument("--max-minutes", type=float, default=10,
                        help="Safety timeout")
    args = parser.parse_args()

    stock = args.stock
    strike_offset = args.strike_offset

    quote_ctx = create_quote_context()
    trd_ctx = create_trade_context()
    pwd = get_demo_trade_password()

    try:
        # Unlock SIMULATE
        ret, _ = trd_ctx.unlock_trade(pwd, trd_env=ft.TrdEnv.SIMULATE)
        if ret != ft.RetCode.SUCCESS:
            logger.warning("unlock_trade: %s (may already be unlocked)", ret)

        # Get spot
        ret, df = quote_ctx.get_stock_quote(stock)
        if ret != ft.RetCode.SUCCESS:
            logger.error("Cannot get quote for %s", stock)
            return
        spot = float(df.iloc[-1]["last_price"])
        target_strike = spot * (1 + strike_offset) if strike_offset else spot

        print(f"\n{'='*70}")
        print(f"  📊 OPTIONS CALENDAR SPREAD BUILDER — {stock}")
        print(f"{'='*70}")
        print(f"  Spot: {spot:.2f}  Target strike: {target_strike:.2f}")

        # Find opportunities
        opps = find_calendar_opportunities(quote_ctx, stock, spot)

        if not opps:
            print("  No calendar spread opportunities found.")
            return

        print(f"\n  Found {len(opps)} potential calendar spreads:\n")
        print(f"  {'#':<3} {'Type':<5} {'Strike':>8} {'Near Exp':>10} {'Near IV':>8} "
              f"{'Far Exp':>10} {'Far IV':>8} {'Vol Sprd':>9} {'Ann Edge':>9}")
        print(f"  {'-'*3} {'-'*5} {'-'*8} {'-'*10} {'-'*8} {'-'*10} {'-'*8} {'-'*9} {'-'*9}")

        for i, opp in enumerate(opps[:10]):
            print(
                f"  {i+1:<3} {opp['type']:<5} {opp['strike']:>8.2f} "
                f"{opp['near_expiry']:>10} {opp['near_iv']:>7.1f}% "
                f"{opp['far_expiry']:>10} {opp['far_iv']:>7.1f}% "
                f"{opp['vol_spread']:>+8.1f}pp {opp['annualised_edge']:>8.1f}%"
            )

        # Offer to execute the best opportunity
        print(f"\n  Execute best opportunity? (0 to skip)")
        try:
            choice = int(input("  Choice: "))
        except (ValueError, EOFError):
            choice = 0

        if 1 <= choice <= len(opps):
            opp = opps[choice - 1]
            print(f"\n  Executing: SELL {opp['near_code']} / BUY {opp['far_code']}")

            # Sell near-term
            ret1, id1 = trd_ctx.place_order(
                price=0, code=opp["near_code"], qty=1,
                trd_side=ft.TrdSide.SELL,
                order_type=ft.OrderType.NORMAL,
                trd_env=ft.TrdEnv.SIMULATE,
                remark="calendar_sell_near",
            )
            # Buy longer-term
            ret2, id2 = trd_ctx.place_order(
                price=0, code=opp["far_code"], qty=1,
                trd_side=ft.TrdSide.BUY,
                order_type=ft.OrderType.NORMAL,
                trd_env=ft.TrdEnv.SIMULATE,
                remark="calendar_buy_far",
            )

            if ret1 == ft.RetCode.SUCCESS and ret2 == ft.RetCode.SUCCESS:
                print(f"  ✅ Calendar spread placed: SELL {id1} / BUY {id2}")
            else:
                print(f"  ❌ Order placement failed: {ret1}, {ret2}")
        else:
            print("  Skipped — no order placed.")

    finally:
        logger.info("Cleaning up …")
        trd_ctx.cancel_all_order(cancel_all_orders=True, trd_env=ft.TrdEnv.SIMULATE)
        quote_ctx.close()
        trd_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()