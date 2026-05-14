#!/usr/bin/env python3
"""
60 — Cross-Market Arbitrage Spread Monitor

Monitors dual-listed stocks across HK and US markets, computing the
theoretical ADR-equivalent price and tracking the spread in real time.

When the spread exceeds configurable thresholds, a signal is printed.

No orders are placed — pure monitoring.

SDK: OpenQuoteContext.subscribe(QUOTE) + StockQuoteHandlerBase
"""

import sys
import time
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

USDHKD = 7.82

PAIRS = [
    {"hk": "HK.00700", "us": "US.TCEHY",  "ratio": 1.0, "name": "Tencent"},
    {"hk": "HK.09988", "us": "US.BABA",   "ratio": 1.0, "name": "Alibaba"},
    {"hk": "HK.09888", "us": "US.BIDU",   "ratio": 8.0, "name": "Baidu"},
    {"hk": "HK.09618", "us": "US.JD",     "ratio": 2.0, "name": "JD.com"},
]

SPREAD_WARN_BPS = 50
SPREAD_DIVERGE_BPS = 150


class CrossMarketSpread:
    def __init__(self, pair: dict):
        self.pair = pair
        self.hk_price: float | None = None
        self.us_price: float | None = None
        self.hk_market: str = "?"
        self.us_market: str = "?"

    @property
    def name(self) -> str:
        return self.pair["name"]

    @property
    def hk_code(self) -> str:
        return self.pair["hk"]

    @property
    def us_code(self) -> str:
        return self.pair["us"]

    @property
    def adr_ratio(self) -> float:
        return self.pair["ratio"]

    @property
    def adr_eq_hkd(self) -> float | None:
        if self.us_price is None:
            return None
        return self.us_price * USDHKD * self.adr_ratio

    @property
    def spread_bps(self) -> float | None:
        if self.hk_price is None or self.adr_eq_hkd is None or self.hk_price == 0:
            return None
        return (self.adr_eq_hkd - self.hk_price) / self.hk_price * 10000

    @property
    def signal(self) -> str:
        s = self.spread_bps
        if s is None:
            return "— waiting"
        if s is not None and s > SPREAD_DIVERGE_BPS:
            return "⬤ HK CHEAP"
        if s is not None and s < -SPREAD_DIVERGE_BPS:
            return "⬤ US CHEAP"
        if s is not None and s > SPREAD_WARN_BPS:
            return "◐ HK cheap"
        if s is not None and s < -SPREAD_WARN_BPS:
            return "◐ US cheap"
        return "● neutral"

    def update_hk(self, price: float | None, market_state: str = "?"):
        self.hk_price = price
        if market_state != "?":
            self.hk_market = market_state

    def update_us(self, price: float | None, market_state: str = "?"):
        self.us_price = price
        if market_state != "?":
            self.us_market = market_state

    def report(self) -> str:
        hkp = f"{self.hk_price:.2f}HKD" if self.hk_price is not None else "N/A"
        usp = f"{self.us_price:.2f}USD" if self.us_price is not None else "N/A"
        adr = f"{self.adr_eq_hkd:.2f}HKD" if self.adr_eq_hkd is not None else "N/A"
        spd = f"{self.spread_bps:+.0f}bps" if self.spread_bps is not None else "N/A"
        sig = self.signal
        return (f"  [{self.name:<10}] HK={hkp} US={usp} "
                f"ADR_eq={adr} spread={spd} {sig}  "
                f"({self.hk_market}/{self.us_market})")


class QuoteHandler(ft.StockQuoteHandlerBase):
    def __init__(self, spreads: list[CrossMarketSpread]):
        super().__init__()
        self.spreads = spreads

    def on_recv_rsp(self, rsp_pb):
        ret_code, content = super().on_recv_rsp(rsp_pb)
        if ret_code != ft.RET_OK:
            return ft.RET_ERROR, content

        code = content.get("code", "")
        price = content.get("last_price", None)
        market = content.get("market_state", "?")

        for s in self.spreads:
            if code == s.hk_code:
                s.update_hk(price, market)
            elif code == s.us_code:
                s.update_us(price, market)

        for s in self.spreads:
            print(s.report())

        return ft.RET_OK, content


def main():
    print("  === Cross-Market Arbitrage Spread Monitor ===\n")
    print(f"  USD/HKD: {USDHKD}")
    print(f"  Warn: >{SPREAD_WARN_BPS}bps  Diverge: >{SPREAD_DIVERGE_BPS}bps\n")

    spreads = [CrossMarketSpread(p) for p in PAIRS]
    for s in spreads:
        print(f"  {s.name:<12} {s.hk_code} ↔ {s.us_code}  ratio={s.adr_ratio}")
    print()

    ctx = create_quote_context()
    ctx.set_handler(QuoteHandler(spreads))

    all_codes = []
    for s in spreads:
        all_codes.append(s.hk_code)
        all_codes.append(s.us_code)

    ret, _ = ctx.subscribe(all_codes, [ft.SubType.QUOTE])
    if ret != 0:
        print(f"  Subscribe failed: {ret}")
        ctx.close()
        return

    print(f"  Listening for quote updates (30s)...\n")
    print(f"  {'='*70}")

    try:
        time.sleep(30)
    except KeyboardInterrupt:
        pass
    finally:
        print(f"\n  {'='*70}")
        ctx.close()


if __name__ == "__main__":
    main()
