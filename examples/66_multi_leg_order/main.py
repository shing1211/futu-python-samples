#!/usr/bin/env python3
"""
66 — Multi-Leg Options Order

Place a multi-leg options strategy (vertical call spread) on a SIMULATE
account. Demonstrates simultaneous order placement, fill monitoring,
and net position reporting.

SIMULATE account only — no real orders.

SDK: OpenSecTradeContext.place_order()
               .order_list_query()
               .position_list_query()
               .cancel_all_order()
               .unlock_trade()
    OpenQuoteContext.get_option_chain()
               .get_option_expiration_date()
               .get_stock_quote()
"""

import sys
import time
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
import futu as ft
from connect import create_quote_context, create_trade_context, get_demo_trade_password
from spreads import VerticalSpread

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

STOCK = "US.NVDA"
TRD_ENV = ft.TrdEnv.SIMULATE
MONITOR_SEC = 30


def find_atm_strikes(ctx, expiry: str, spot: float):
    ret, chain = ctx.get_option_chain(
        STOCK, start=expiry, end=expiry, option_type=ft.OptionType.CALL,
    )
    if ret != 0 or chain is None or chain.empty:
        return None, None

    strikes = []
    for _, row in chain.iterrows():
        strike = float(row.get("strike_price", 0))
        bid = float(row.get("bid_price", 0))
        ask = float(row.get("ask_price", 0))
        if strike > 0:
            strikes.append({"strike": strike, "bid": bid, "ask": ask})

    strikes.sort(key=lambda x: x["strike"])
    atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i]["strike"] - spot))

    if atm_idx == 0 or atm_idx >= len(strikes) - 1:
        return None, None

    long_leg = strikes[atm_idx - 1]
    short_leg = strikes[atm_idx + 1]

    return long_leg, short_leg


def main():
    print(f"  === Multi-Leg Options Order ===\n")
    print(f"  IMPORTANT: SIMULATE account only. No real orders.\n")
    print(f"  Strategy: Vertical Call Spread (BUY lower strike, SELL higher strike)")
    print(f"  Stock: {STOCK}\n")

    quote_ctx = create_quote_context()
    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.ALL)

    try:
        ret, data = trd_ctx.unlock_trade(get_demo_trade_password())
        if ret != ft.RET_OK:
            print(f"  unlock_trade failed: {data}")
            return

        ret2, expirations = quote_ctx.get_option_expiration_date(
            STOCK, ft.IndexOptionType.NORMAL,
        )
        if ret2 != 0:
            print(f"  get_option_expiration_date failed: {expirations}")
            return

        expiry = None
        if isinstance(expirations, list) and len(expirations) > 0:
            expiry = str(expirations[0])[:10]
        elif hasattr(expirations, "iloc") and len(expirations) > 0:
            expiry = str(expirations.iloc[0].get("strike_time", ""))[:10]

        if not expiry:
            print(f"  No expirations found for {STOCK}")
            return

        ret3, quotes = quote_ctx.get_stock_quote([STOCK])
        spot = 0.0
        if ret3 == ft.RET_OK and quotes is not None and not quotes.empty:
            spot = float(quotes.iloc[0].get("last_price", 0))

        if spot <= 0:
            print(f"  No valid price for {STOCK}")
            return

        print(f"  Spot: {spot:.2f} | Expiry: {expiry}\n")

        long_leg, short_leg = find_atm_strikes(quote_ctx, expiry, spot)
        if long_leg is None or short_leg is None:
            print(f"  Could not determine strikes near {spot:.2f}")
            return

        spread = VerticalSpread(
            underlying=STOCK, expiry=expiry,
            strike_long=long_leg["strike"], strike_short=short_leg["strike"],
            bid_long=long_leg["bid"], ask_long=long_leg["ask"],
            bid_short=short_leg["bid"], ask_short=short_leg["ask"],
        )

        print(spread.summary())
        print()

        if spread.net_debit <= 0:
            print(f"  Net debit <= 0 — spread not executable at current prices, skipping")
            return

        leg1_code = f"{STOCK}{expiry}C{long_leg['strike']:.0f}"
        leg2_code = f"{STOCK}{expiry}C{short_leg['strike']:.0f}"

        print(f"  Placing orders (1 contract each)...")
        r1, o1 = trd_ctx.place_order(
            price=spread.ask_long, qty=1, code=leg1_code,
            trd_side=ft.TrdSide.BUY, order_type=ft.OrderType.NORMAL,
            trd_env=TRD_ENV,
        )
        r2, o2 = trd_ctx.place_order(
            price=spread.bid_short, qty=1, code=leg2_code,
            trd_side=ft.TrdSide.SELL, order_type=ft.OrderType.NORMAL,
            trd_env=TRD_ENV,
        )
        leg1_id = o1.get("order_id", "N/A") if r1 == ft.RET_OK else f"FAILED({o1})"
        leg2_id = o2.get("order_id", "N/A") if r2 == ft.RET_OK else f"FAILED({o2})"
        print(f"  Leg 1 (BUY  {long_leg['strike']:.0f}C): {leg1_id}")
        print(f"  Leg 2 (SELL {short_leg['strike']:.0f}C): {leg2_id}")

        filled_leg1 = False
        filled_leg2 = False
        print(f"\n  Monitoring fills for {MONITOR_SEC}s...")
        for i in range(MONITOR_SEC // 5):
            time.sleep(5)
            r3, orders = trd_ctx.order_list_query(trd_env=TRD_ENV)
            if r3 == ft.RET_OK and orders is not None and not orders.empty:
                for _, o in orders.iterrows():
                    oid = str(o.get("order_id", ""))
                    status = str(o.get("order_status", o.get("status", "")))
                    if oid == leg1_id and status in ("FILLED_ALL", "FILLED_PART"):
                        filled_leg1 = True
                    if oid == leg2_id and status in ("FILLED_ALL", "FILLED_PART"):
                        filled_leg2 = True
            print(f"  [{i*5+5}s] Leg1={'✅' if filled_leg1 else '⏳'} "
                  f"Leg2={'✅' if filled_leg2 else '⏳'}")

        print(f"\n  {'='*50}")
        if filled_leg1 and filled_leg2:
            print(f"  BOTH LEGS FILLED — position open")
            print(f"  Net debit: {spread.net_debit:.2f}")
            print(f"  Max profit: {spread.max_profit:.2f}")
            print(f"  Max loss:   {spread.max_loss:.2f}")
        else:
            print(f"  Partial fill risk:")
            if filled_leg1:
                print(f"    Leg 1 filled (long) — naked short if Leg 2 unfilled")
            if filled_leg2:
                print(f"    Leg 2 filled (short) — uncovered if Leg 1 unfilled")
            if not filled_leg1 and not filled_leg2:
                print(f"    Neither leg filled")

    finally:
        print(f"\n  Cleaning up...")
        r4, _ = trd_ctx.cancel_all_order(trd_env=TRD_ENV)
        print(f"  cancel_all_order: ret={r4}")
        quote_ctx.close()
        trd_ctx.close()
        print(f"  Done.")


if __name__ == "__main__":
    main()
