#!/usr/bin/env python3
"""
63 — Earnings Volatility Screener

Two-phase earnings screener:
  Phase 1 — Pre-earnings: fetch ATM option IV, compare to historical vol.
  Phase 2 — Post-earnings: check unusual volume/price activity.

No order placement — pure screening.

SDK: OpenQuoteContext.get_option_chain()
               .get_option_expiration_date()
               .get_technical_unusual()
               .get_financial_unusual()
"""

import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

STOCKS = [
    ("US.NVDA",  "NVIDIA",     "2026-05-28"),
    ("US.AAPL",  "Apple",      "2026-07-23"),
    ("US.TSLA",  "Tesla",      "2026-07-16"),
    ("US.MSFT",  "Microsoft",  "2026-07-16"),
    ("US.AMZN",  "Amazon",     "2026-07-30"),
    ("US.META",  "Meta",       "2026-07-29"),
    ("US.GOOGL", "Alphabet",   "2026-07-23"),
]


def compute_hv(closes: list[float], period: int = 20) -> float:
    if len(closes) < period + 1:
        return 0.0
    log_returns = []
    for i in range(1, period + 1):
        if closes[-i - 1] != 0:
            log_returns.append(__import__("math").log(closes[-i] / closes[-i - 1]))
    if not log_returns:
        return 0.0
    mean_r = sum(log_returns) / len(log_returns)
    var_r = sum((r - mean_r) ** 2 for r in log_returns) / len(log_returns)
    return (var_r ** 0.5) * (252 ** 0.5)


def phase1_pre_earnings(ctx, code: str, name: str, earnings_date: str):
    print(f"\n  --- {name} ({code}) ---")

    ret, expirations = ctx.get_option_expiration_date(code)
    if ret != 0:
        print(f"    No option expirations: {expirations}")
        return

    earnings_dt = datetime.strptime(earnings_date, "%Y-%m-%d")
    nearest_expiry = None
    nearest_dist = 999

    if isinstance(expirations, list):
        for d in expirations:
            exp_dt = datetime.strptime(str(d)[:10], "%Y-%m-%d")
            dist = abs((exp_dt - earnings_dt).days)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_expiry = str(d)[:10]
    elif hasattr(expirations, "iloc"):
        for _, row in expirations.iterrows():
            d = str(row.get("strike_time", ""))[:10]
            if d:
                exp_dt = datetime.strptime(d, "%Y-%m-%d")
                dist = abs((exp_dt - earnings_dt).days)
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_expiry = d

    if not nearest_expiry:
        print(f"    No suitable expiry found near {earnings_date}")
        return

    ret, chain = ctx.get_option_chain(code, start=nearest_expiry, end=nearest_expiry,
                                      option_type=ft.OptionType.CALL)
    if ret != 0 or chain is None or chain.empty:
        print(f"    No option chain for {nearest_expiry}")
        return

    ivs = []
    for _, row in chain.iterrows():
        iv = float(row.get("implied_volatility", 0))
        if iv > 0:
            ivs.append(iv)

    if not ivs:
        print(f"    No IV data")
        return

    atm_iv = sum(ivs) / len(ivs)

    ret2, klines = ctx.request_history_kline(code, start="", end="",
                                              ktype=ft.KLType.K_DAY,
                                              autype=ft.AuType.QFQ, max_count=50)
    hv = 0.0
    hv_period = 20
    if ret2 == 0 and klines is not None and not klines.empty:
        closes = klines["close"].tolist()
        hv = compute_hv(closes, hv_period) if len(closes) > hv_period else 0.0

    ratio = atm_iv / hv if hv > 0 else 0

    signal = "—"
    if ratio > 2.0:
        signal = "⬤ IV EXTREMELY ELEVATED — earnings priced in"
    elif ratio > 1.5:
        signal = "◐ IV elevated — premium rich"

    print(f"    Earnings: {earnings_date}  Nearest expiry: {nearest_expiry} ({nearest_dist}d away)")
    print(f"    ATM IV:    {atm_iv*100:.1f}%")
    print(f"    {hv_period}d HV:    {hv*100:.1f}%")
    print(f"    IV/HV:     {ratio:.2f}x")
    print(f"    Signal:    {signal}")


def phase2_post_earnings(ctx, code: str, name: str, earnings_date: str):
    print(f"\n  --- {name} ({code}) post-earnings ---")

    ed = datetime.strptime(earnings_date, "%Y-%m-%d")
    start = (ed - timedelta(days=1)).strftime("%Y-%m-%d")
    end = (ed + timedelta(days=5)).strftime("%Y-%m-%d")

    ret, tech = ctx.get_technical_unusual(code)
    if ret == 0 and tech is not None and not tech.empty:
        print(f"    Technical unusual detected:")
        for _, row in tech.iterrows():
            print(f"      {row.get('code','')} {row.get('unusual_type','')} "
                  f"value={row.get('value','')} desc={row.get('desc','')}")
    else:
        print(f"    No technical anomalies")

    ret, fin = ctx.get_financial_unusual(code)
    if ret == 0 and fin is not None and not fin.empty:
        print(f"    Financial unusual detected:")
        for _, row in fin.iterrows():
            print(f"      {row.get('unusual_type','')} "
                  f"value={row.get('value','')} desc={row.get('desc','')}")
    else:
        print(f"    No financial anomalies")


def main():
    print(f"  === Earnings Volatility Screener ===\n")
    print(f"  Scanning {len(STOCKS)} stocks\n")

    ctx = create_quote_context()

    try:
        print(f"  {'='*60}")
        print(f"  PHASE 1 — PRE-EARNINGS IV SCAN")
        print(f"  {'='*60}")

        for code, name, earnings_date in STOCKS:
            phase1_pre_earnings(ctx, code, name, earnings_date)
        print()

        print(f"  {'='*60}")
        print(f"  PHASE 2 — POST-EARNINGS UNUSUAL ACTIVITY")
        print(f"  {'='*60}")

        for code, name, earnings_date in STOCKS:
            phase2_post_earnings(ctx, code, name, earnings_date)
        print()

    finally:
        ctx.close()


if __name__ == "__main__":
    main()
