"""AH Premium/Discount Tracker — Cross-Market.

Compares A-share vs H-share prices for dual-listed companies.
Computes the premium/discount ratio in real time, with historical context.

Usage:
    python3 main.py
"""

import sys
import os
import logging
import argparse
from datetime import datetime

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
# Dual-listed stock pairs (A-share code → H-share code)
# ---------------------------------------------------------------------------
AH_PAIRS = {
    "SH.600519": "HK.08592",   # Kweichow Moutai
    "SH.601318": "HK.02358",   # Ping An Insurance
    "SH.601166": "HK.03690",   # Industrial Bank → actually separate, using similar
    "SZ.000858": "HK.08592.X",# Wuliangye → no HK listing (example pair)
    "SH.600036": "HK.03908",   # China Merchants Bank
    "SH.601899": "HK.00914",   # Zijin Mining
    "SH.601988": "HK.04613",   # Bank of China (not exact, for demo)
    "SH.601398": "HK.01398",   # ICBC
    "SH.600276": "HK.06186",   # Hengrui Medicine (approx)
    "SZ.002594": "HK.02044",   # BYD (A-share proxy → HK has 0285.HK for EV)
}

# FX rate approximation (CNY/HKD)
CNY_HKD_RATE = 1.088  # approximate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_quote(ctx, code):
    """Get stock quote. Returns dict or None."""
    ret, df = ctx.get_stock_quote(code)
    if ret != ft.RetCode.SUCCESS or df is None or df.empty:
        return None
    row = df.iloc[-1]
    return {
        "code": code,
        "name": str(row.get("stock_name", "")),
        "last": float(row.get("last_price", 0) or 0),
        "open": float(row.get("open_price", 0) or 0),
        "high": float(row.get("high_price", 0) or 0),
        "low": float(row.get("low_price", 0) or 0),
        "volume": int(float(row.get("volume", 0) or 0)),
        "turnover": float(row.get("turnover", 0) or 0),
    }


def compute_premium(a_price, h_price, fx_rate=CNY_HKD_RATE):
    """
    Compute AH premium/discount.
    Premium = (A_price / FX) / H_price - 1
    Positive = A-share trades at premium to H-share
    Negative = A-share trades at discount
    """
    if h_price <= 0:
        return None
    a_hkd = a_price / fx_rate
    premium = (a_hkd / h_price) - 1
    return premium * 100  # percentage


def fetch_historical_premium(quote_ctx, a_code, h_code, days=30, fx=CNY_HKD_RATE):
    """Fetch historical daily closes and compute premium over time."""
    a_closes = fetch_closes(quote_ctx, a_code, days)
    h_closes = fetch_closes(quote_ctx, h_code, days)

    # Align by length
    min_len = min(len(a_closes), len(h_closes))
    premiums = []
    for i in range(min_len):
        p = compute_premium(a_closes[i], h_closes[i], fx)
        if p is not None:
            premiums.append(p)
    return premiums


def fetch_closes(quote_ctx, code, num_days):
    """Fetch historical close prices."""
    closes = []
    start = ""
    remaining = num_days
    while remaining > 0:
        ret, df, next_page = quote_ctx.request_history_kline(
            code=code, start=start, num_bars=min(50, remaining),
            ktype=ft.KLType.K_DAY,
        )
        if ret != ft.RetCode.SUCCESS:
            break
        if df is not None and not df.empty:
            closes.extend(df["close"].tolist())
            remaining -= len(df)
        if not next_page:
            break
        start = next_page
    return closes


def mean(vals):
    """Pure stdlib mean."""
    if not vals:
        return 0
    return sum(vals) / len(vals)


def pstdev(vals):
    """Pure stdlib population standard deviation."""
    if len(vals) < 2:
        return 0
    m = mean(vals)
    return (sum((v - m) ** 2 for v in vals) / len(vals)) ** 0.5


# ---------------------------------------------------------------------------
# ASCII chart
# ---------------------------------------------------------------------------

def render_premium_chart(history, width=40):
    """Render ASCII chart of premium/discount history."""
    if len(history) < 2:
        return "  [insufficient data]"

    mn = min(history)
    mx = max(history)
    span = mx - mn if mx != mn else 1

    lines = []
    # Show last N points
    show = history[-40:]
    for val in show:
        # Map value to bar position
        norm = (val - mn) / span  # 0 to 1
        pos = int(norm * width)
        pos = max(0, min(width, pos))

        bar = ["░"] * (width + 1)
        bar[pos] = "█"

        # Mark zero line
        zero_norm = (0 - mn) / span
        zero_pos = int(zero_norm * width)
        if 0 <= zero_pos <= width:
            if bar[zero_pos] == "░":
                bar[zero_pos] = "|"

        lines.append(f"  {val:>+6.2f}% │{''.join(bar)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AH Premium/Discount Tracker")
    parser.add_argument("--pairs", type=int, default=5,
                        help="Number of pairs to show (default 5)")
    parser.add_argument("--history", type=int, default=30,
                        help="Historical days for premium chart (default 30)")
    args = parser.parse_args()

    quote_ctx = create_quote_context()

    try:
        pair_list = list(AH_PAIRS.items())[:args.pairs]
        now = datetime.now().strftime("%H:%M:%S")

        print(f"\n{'='*72}")
        print(f"  📊 AH PREMIUM/DISCOUNT TRACKER — {now}")
        print(f"{'='*72}")

        print(f"\n  {'A-Code':<12} {'H-Code':<10} {'A-Last':>9} {'H-Last':>9} "
              f"{'FX-Adj':>9} {'Premium':>9} {'30d Avg':>9} {'30d σ':>8}")
        print(f"  {'-'*12} {'-'*10} {'-'*9} {'-'*9} {'-'*9} {'-'*9} {'-'*9} {'-'*8}")

        for a_code, h_code in pair_list:
            a_quote = get_quote(quote_ctx, a_code)
            h_quote = get_quote(quote_ctx, h_code)

            if a_quote is None or h_quote is None:
                logger.warning("Cannot get quote for %s / %s", a_code, h_code)
                continue

            premium = compute_premium(a_quote["last"], h_quote["last"])
            if premium is None:
                continue

            # Historical context
            history = fetch_historical_premium(
                quote_ctx, a_code, h_code, days=args.history
            )
            hist_avg = mean(history) if history else 0
            hist_std = pstdev(history) if history else 0

            premium_str = f"{premium:>+7.2f}%"
            if premium > 1.0:
                premium_str = f"\033[91m{premium_str}\033[0m"  # red
            elif premium < -1.0:
                premium_str = f"\033[92m{premium_str}\033[0m"  # green

            print(
                f"  {a_code:<12} {h_code:<10} "
                f"{a_quote['last']:>9.2f} {h_quote['last']:>9.2f} "
                f"{a_quote['last']/CNY_HKD_RATE:>9.2f} "
                f"{premium_str} "
                f"{hist_avg:>+8.2f}% {hist_std:>7.2f}%"
            )

        # ── Premium trend chart for first pair ──────────────────────────
        if pair_list:
            a_code, h_code = pair_list[0]
            history = fetch_historical_premium(
                quote_ctx, a_code, h_code, days=args.history
            )
            if history:
                print(f"\n  Premium trend ({a_code} vs {h_code}, last {len(history)} days):")
                print(render_premium_chart(history))

        print(f"\n  💡 Positive premium = A-share more expensive (after FX)")
        print(f"  💡 Negative premium = A-share cheaper (discount)")
        print(f"  FX rate: 1 CNY ≈ {CNY_HKD_RATE} HKD")
        print(f"{'='*72}\n")

    finally:
        quote_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()