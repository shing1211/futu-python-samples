"""Multi-Leg Options Strategy Execution — SIMULATE only.

Builds and executes multi-leg options strategies (straddle, strangle, iron condor)
using the Futu options API. Legs are placed together and monitored for fills.

Usage:
    python3 main.py --strategy straddle --stock HK.00700 --expiry 202606
    python3 main.py --strategy iron_condor --stock HK.00700
"""

import sys
import logging
import argparse
import time

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

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

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

STRATEGIES = {}


def register_strategy(name):
    """Decorator to register a strategy builder."""
    def decorator(fn):
        STRATEGIES[name] = fn
        return fn
    return decorator


@register_strategy("straddle")
def build_straddle(quote_ctx, stock, expiry, target_price):
    """Straddle: buy 1 call + 1 put at same strike (ATM).

    Legs:
      - Long Call @ ATM strike
      - Long Put  @ ATM strike
    Profit: large move in either direction.
    """
    return [
        {
            "code": _find_option(quote_ctx, stock, expiry, target_price, "call"),
            "trd_side": ft.TrdSide.BUY,
            "qty": 1,
            "remark": "straddle_call",
        },
        {
            "code": _find_option(quote_ctx, stock, expiry, target_price, "put"),
            "trd_side": ft.TrdSide.BUY,
            "qty": 1,
            "remark": "straddle_put",
        },
    ]


@register_strategy("strangle")
def build_strangle(quote_ctx, stock, expiry, target_price):
    """Strangle: buy OTM call + OTM put (different strikes).

    Legs:
      - Long Call @ target + 3 %
      - Long Put  @ target - 3 %
    Profit: large move in either direction (cheaper than straddle).
    """
    call_strike = round(target_price * 1.03, 2)
    put_strike = round(target_price * 0.97, 2)
    return [
        {
            "code": _find_option(quote_ctx, stock, expiry, call_strike, "call"),
            "trd_side": ft.TrdSide.BUY,
            "qty": 1,
            "remark": "strangle_call",
        },
        {
            "code": _find_option(quote_ctx, stock, expiry, put_strike, "put"),
            "trd_side": ft.TrdSide.BUY,
            "qty": 1,
            "remark": "strangle_put",
        },
    ]


@register_strategy("iron_condor")
def build_iron_condor(quote_ctx, stock, expiry, target_price):
    """Iron Condor: sell OTM call spread + sell OTM put spread.

    Legs:
      - Short Call @ target + 2 %
      - Long  Call @ target + 5 % (hedge)
      - Short Put  @ target - 2 %
      - Long  Put  @ target - 5 % (hedge)
    Profit: price stays within inner strikes.
    """
    strikes = {
        "short_call": round(target_price * 1.02, 2),
        "long_call":  round(target_price * 1.05, 2),
        "short_put":  round(target_price * 0.98, 2),
        "long_put":   round(target_price * 0.95, 2),
    }
    return [
        {
            "code": _find_option(quote_ctx, stock, expiry, strikes["short_call"], "call"),
            "trd_side": ft.TrdSide.SELL,
            "qty": 1,
            "remark": "ic_short_call",
        },
        {
            "code": _find_option(quote_ctx, stock, expiry, strikes["long_call"], "call"),
            "trd_side": ft.TrdSide.BUY,
            "qty": 1,
            "remark": "ic_long_call_hedge",
        },
        {
            "code": _find_option(quote_ctx, stock, expiry, strikes["short_put"], "put"),
            "trd_side": ft.TrdSide.SELL,
            "qty": 1,
            "remark": "ic_short_put",
        },
        {
            "code": _find_option(quote_ctx, stock, expiry, strikes["long_put"], "put"),
            "trd_side": ft.TrdSide.BUY,
            "qty": 1,
            "remark": "ic_long_put_hedge",
        },
    ]


# ---------------------------------------------------------------------------
# Option helpers
# ---------------------------------------------------------------------------

def _find_option(quote_ctx, stock, expiry, strike, option_type):
    """Find an option contract matching the criteria.

    Uses get_option_chain to search available contracts.
    Returns the stock_code string or raises if not found.
    """
    min_val = strike * 0.98
    max_val = strike * 1.02

    start = ""
    for _ in range(5):
        ret, df, next_page = quote_ctx.get_option_chain(
            code=stock,
            num=20,
            start=start,
            option_type=0,  # all types
        )
        if ret != ft.RetCode.SUCCESS or df is None or df.empty:
            break

        for _, row in df.iterrows():
            code = str(row.get("code", ""))
            name = str(row.get("stock_name", ""))

            # Match expiry
            if expiry and str(row.get("end_date", ""))[:6] != str(expiry)[:6]:
                continue

            # Match type
            type_match = False
            if option_type == "call":
                type_match = "CALL" in name.upper() or "Call" in name
            elif option_type == "put":
                type_match = "PUT" in name.upper() or "Put" in name
            else:
                type_match = True

            if not type_match:
                continue

            # Match strike
            row_strike = float(row.get("exercise_price", 0) or
                               row.get("strike_price", 0) or 0)
            if row_strike == 0:
                continue

            # For ATM straddle, find closest to target
            if strike > 0 and abs(row_strike - strike) < (strike * 0.02):
                logger.info("  Found %s %s strike=%.2f code=%s",
                            "Call" if "call" in option_type else "Put",
                            expiry, row_strike, code)
                return code

        if not next_page:
            break
        start = next_page

    # Fallback: broader search with wider tolerance
    logger.warning("Exact strike not found, trying wider range for %s %.2f…",
                    option_type, strike)
    start = ""
    for _ in range(5):
        ret, df, next_page = quote_ctx.get_option_chain(
            code=stock, num=50, start=start,
        )
        if ret != ft.RetCode.SUCCESS or df is None or df.empty:
            break
        for _, row in df.iterrows():
            code = str(row.get("code", ""))
            name = str(row.get("stock_name", ""))
            if expiry and str(row.get("end_date", ""))[:6] != str(expiry)[:6]:
                continue
            type_match = ("CALL" in name.upper()) == (option_type == "call")
            if not type_match:
                continue
            row_strike = float(row.get("exercise_price", 0) or
                               row.get("strike_price", 0) or 0)
            if row_strike > 0:
                logger.info("  Found %s strike=%.2f code=%s",
                            "Call" if "call" in option_type else "Put",
                            row_strike, code)
                return code
        if not next_page:
            break
        start = next_page

    raise ValueError(
        f"No option found for {stock} {option_type} "
        f"strike≈{strike} expiry≈{expiry}"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Multi-leg options strategy (SIMULATE)")
    parser.add_argument("--strategy", choices=list(STRATEGIES.keys()),
                        default="straddle",
                        help="Strategy to execute (default: straddle)")
    parser.add_argument("--stock", default="HK.00700", help="Underlying stock")
    parser.add_argument("--expiry", default="",
                        help="Expiry YYYYMM (empty = first available)")
    parser.add_argument("--max-minutes", type=float, default=10,
                        help="Safety timeout")
    args = parser.parse_args()

    strategy_name = args.strategy
    stock = args.stock
    expiry = args.expiry
    max_seconds = args.max_minutes * 60

    builder = STRATEGIES.get(strategy_name)
    if not builder:
        logger.error("Unknown strategy: %s. Available: %s",
                     strategy_name, ", ".join(STRATEGIES))
        return

    quote_ctx = create_quote_context()
    trd_ctx = create_trade_context()

    try:
        # ── Get current price for ATM strike ──────────────────────────
        ret, df = quote_ctx.get_stock_quote(stock)
        if ret != ft.RetCode.SUCCESS:
            logger.error("Cannot get quote for %s", stock)
            return
        target_price = float(df.iloc[-1]["last_price"])
        logger.info("%s current price: %.2f", stock, target_price)

        # ── Build legs ─────────────────────────────────────────────────
        logger.info("Building %s strategy …", strategy_name)
        try:
            legs = builder(quote_ctx, stock, expiry, target_price)
        except ValueError as e:
            logger.error(str(e))
            return

        print(f"\n{'='*60}")
        print(f"  📊 {strategy_name.upper()} — {stock}")
        print(f"{'='*60}")
        for i, leg in enumerate(legs):
            print(f"  Leg {i+1}: {leg['trd_side'].name:<4} "
                  f"{leg['code']}  qty={leg['qty']}  ({leg['remark']})")
        print(f"{'='*60}\n")

        # ── Check prices before placing ────────────────────────────────
        total_cost = 0
        for leg in legs:
            ret_o, df_o = quote_ctx.get_stock_quote(leg["code"])
            if ret_o == ft.RetCode.SUCCESS:
                price = float(df_o.iloc[-1]["last_price"])
                total_cost += price * leg["qty"]
                print(f"  {leg['code']} last price: {price:.4f}")
            else:
                logger.warning("Cannot get quote for %s", leg["code"])

        print(f"  Estimated total cost: {total_cost:.2f}")

        # ── Place legs ─────────────────────────────────────────────────
        order_ids = []
        for leg in legs:
            ret, order_id = trd_ctx.place_order(
                price=0,  # market
                code=leg["code"],
                qty=leg["qty"],
                trd_side=leg["trd_side"],
                order_type=ft.OrderType.NORMAL,
                trd_env=ft.TrdEnv.SIMULATE,
                remark=leg["remark"],
            )
            if ret == ft.RetCode.SUCCESS:
                order_ids.append(order_id)
                logger.info("  ✅ %s %s → %s", leg["trd_side"].name,
                            leg["code"], order_id)
            else:
                logger.error("  ❌ %s %s failed: %s",
                             leg["trd_side"].name, leg["code"], ret)

        logger.info("Placed %d / %d legs.", len(order_ids), len(legs))

        # ── Monitor fills ──────────────────────────────────────────────
        deadline = time.time() + max_seconds
        while time.time() < deadline:
            time.sleep(5)
            if not order_ids:
                break
            ret, orders = trd_ctx.order_list_query(trd_env=ft.TrdEnv.SIMULATE)
            if ret != ft.RetCode.SUCCESS:
                continue
            filled = 0
            for _, row in orders.iterrows():
                if row["order_id"] in order_ids:
                    status = row["order_status"]
                    if status in (ft.OrderStatus.FILLED_ALL,
                                  ft.OrderStatus.FILLED_PART):
                        filled += 1
            if filled >= len(order_ids):
                logger.info("🎉 All %d legs filled!", len(order_ids))
                break
            if filled > 0:
                logger.info("⏳ %d / %d legs filled", filled, len(order_ids))

    finally:
        logger.info("Cleaning up …")
        trd_ctx.cancel_all_order(cancel_all_orders=True,
                                 trd_env=ft.TrdEnv.SIMULATE)
        quote_ctx.close()
        trd_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()