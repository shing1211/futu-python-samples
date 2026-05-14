#!/usr/bin/env python3
"""
58 — Options Greeks Dashboard

Subscribe to an optionable stock, fetch the option chain, compute the five
Black-Scholes Greeks (delta, gamma, theta, vega, rho), and print a live table.

No order placement — pure monitoring and computation.

SDK: OpenQuoteContext.get_option_chain()
               .get_option_expiration_date()
               .get_stock_quote()
               .subscribe(QUOTE) + StockQuoteHandlerBase
"""

import sys
import time
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
import futu as ft
from connect import create_quote_context
from greeks import compute_greeks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

STOCK = "US.NVDA"
RISK_FREE_RATE = 0.045
REFRESH_SEC = 30


def get_nearest_expiry(ctx):
    ret, dates = ctx.get_option_expiration_date(STOCK, ft.IndexOptionType.NORMAL)
    if ret != 0:
        print(f"  get_option_expiration_date failed: {dates}")
        return None
    if isinstance(dates, list) and len(dates) > 0:
        return dates[0]
    if hasattr(dates, "iloc") and len(dates) > 0:
        return dates.iloc[0]["strike_time"]
    return None


def fetch_greeks(ctx, expiry: str, underlying_price: float):
    rows = []
    for opt_type, label in [(ft.OptionType.CALL, "CALL"), (ft.OptionType.PUT, "PUT")]:
        ret, chain = ctx.get_option_chain(
            STOCK, start=expiry, end=expiry, option_type=opt_type,
        )
        if ret != 0:
            continue
        if chain is None or chain.empty:
            continue
        for _, row in chain.iterrows():
            strike = float(row.get("strike_price", 0))
            iv = float(row.get("implied_volatility", 0))
            last_price = float(row.get("last_price", 0))
            now = time.time()
            days_to_expiry = float(row.get("option_expiry_date_distance",
                                           row.get("days_to_expiry", 30)))
            T = max(days_to_expiry, 1.0) / 365.0
            if iv <= 0:
                continue
            greeks = compute_greeks(underlying_price, strike, T, RISK_FREE_RATE, iv, label)
            rows.append({
                "strike": strike,
                "type": label,
                "iv": iv,
                "last": last_price,
                **greeks,
            })
    return rows


def print_table(rows: list, underlying: float):
    print(f"\n  Underlying: {STOCK} @ {underlying:.2f}")
    print(f"  Risk-free rate: {RISK_FREE_RATE*100:.1f}%")
    print(f"  {'Strike':>8} {'Type':<5} {'IV':>7} {'Delta':>8} {'Gamma':>9} "
          f"{'Theta':>8} {'Vega':>8} {'Rho':>8} {'Price':>8}")
    print(f"  {'-'*8} {'-'*5} {'-'*7} {'-'*8} {'-'*9} "
          f"{'-'*8} {'-'*8} {'-'*8} {'-'*8}")
    for r in rows[:20]:
        d = f"{r['delta']:.4f}" if r['delta'] is not None else "N/A"
        g = f"{r['gamma']:.6f}" if r['gamma'] is not None else "N/A"
        th = f"{r['theta']:.4f}" if r['theta'] is not None else "N/A"
        v = f"{r['vega']:.4f}" if r['vega'] is not None else "N/A"
        rh = f"{r['rho']:.4f}" if r['rho'] is not None else "N/A"
        p = f"{r['last']:.2f}" if r['last'] else "—"
        print(f"  {r['strike']:>8.0f} {r['type']:<5} {r['iv']*100:>6.1f}% "
              f"{d:>8} {g:>9} {th:>8} {v:>8} {rh:>8} {p:>8}")
    if len(rows) > 20:
        print(f"  ... {len(rows) - 20} more rows")


class QuoteHandler(ft.StockQuoteHandlerBase):
    def __init__(self):
        super().__init__()
        self.last_price: float | None = None
        self.last_refresh: float = 0

    def on_recv_rsp(self, rsp_pb):
        ret_code, content = super().on_recv_rsp(rsp_pb)
        if ret_code != ft.RET_OK:
            return ft.RET_ERROR, content
        self.last_price = content.get("last_price", self.last_price)
        return ft.RET_OK, content

    def needs_refresh(self) -> bool:
        return time.time() - self.last_refresh > REFRESH_SEC


def main():
    print(f"  === Options Greeks Dashboard ===\n")
    print(f"  Stock: {STOCK}")
    print(f"  Risk-free rate: {RISK_FREE_RATE*100:.1f}%")
    print(f"  Greeks refresh: every {REFRESH_SEC}s\n")

    ctx = create_quote_context()
    handler = QuoteHandler()
    ctx.set_handler(handler)

    ret, _ = ctx.subscribe(STOCK, ft.SubType.QUOTE)
    if ret != 0:
        print(f"  Subscribe failed: {ret}")
        ctx.close()
        return

    expiry = get_nearest_expiry(ctx)
    if expiry is None:
        print(f"  No option expiration available for {STOCK}")
        ctx.close()
        return

    print(f"  Nearest expiry: {expiry}\n")

    ret, quotes = ctx.get_stock_quote([STOCK])
    if ret == 0 and quotes is not None and not quotes.empty:
        handler.last_price = float(quotes.iloc[0].get("last_price", 0))
    else:
        ret2, snap = ctx.get_market_snapshot([STOCK])
        if ret2 == 0 and snap is not None and not snap.empty:
            handler.last_price = float(snap.iloc[0].get("last_price", 0))

    try:
        while True:
            if handler.last_price is not None and handler.needs_refresh():
                rows = fetch_greeks(ctx, expiry, handler.last_price)
                handler.last_refresh = time.time()
                if rows:
                    print_table(rows, handler.last_price)
                else:
                    print(f"  No option data for {STOCK} expiry {expiry}")
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        ctx.close()


if __name__ == "__main__":
    main()
