#!/usr/bin/env python3
"""
55 — Multi-Timeframe Momentum Screener

Fetches historical K-lines across THREE timeframes (daily, 60M, 15M)
for a list of stocks and computes RSI + MACD on each.

When all three timeframes agree on the same direction, the signal is
strong.  A "triple confirmation" buy fires when:
  - Daily RSI < 35  (oversold, upside room)
  - 60M RSI < 40    (short-term also oversold)
  - 15M RSI < 45    (immediate-term confirming)
  - Daily MACD histogram > 0  (momentum turning up)

The stocks are sorted by RSI score (most oversold first) so the
strongest candidates float to the top.

What you'll see:
  Per-stock table showing timeframe, RSI, MACD histogram, and a
  composite signal badge (TRIPLE BUY / DOUBLE BUY / WATCH / NEUTRAL).

  At the end: ranked list of stocks sorted by conviction score.

SDK: OpenQuoteContext.request_history_kline() — the paginated version
     of get_history_kline that supports cursor-based pagination.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import futu as ft
from connect import create_quote_context


# ── Indicators ───────────────────────────────────────────────────────────────

def compute_rsi(closes: list[float], period: int = 14) -> float:
    """Relative Strength Index — no numpy/pandas needed."""
    if len(closes) < period + 1:
        return 50.0
    gains, losses = 0.0, 0.0
    for i in range(1, period + 1):
        delta = closes[-i] - closes[-i - 1]
        if delta > 0:
            gains += delta
        else:
            losses -= delta
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_macd(closes: list[float],
                 fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD histogram: (EMA_fast - EMA_slow) minus signal EMA of MACD line."""
    def ema(data, n):
        k = 2.0 / (n + 1)
        ema_val = data[0]
        result = [ema_val]
        for v in data[1:]:
            ema_val = v * k + ema_val * (1 - k)
            result.append(ema_val)
        return result

    if len(closes) < slow + signal:
        return 0.0

    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = ema(macd_line, signal)
    # Return the last histogram value
    return macd_line[-1] - signal_line[-1]


# ── Per-timeframe fetch ──────────────────────────────────────────────────────

def fetch_closes(ctx, code: str, subtype: ft.SubType, max_count: int = 300):
    """request_history_kline with manual pagination — returns flat list of closes."""
    closes = []
    page_key = None
    while len(closes) < max_count:
        ret, data, page_key = ctx.request_history_kline(
            code=code,
            start=None,
            end=None,
            ktype=subtype,
            autype=ft.AuType.QFQ,
            max_count=min(800, max_count - len(closes)),
            page_req_key=page_key,
        )
        if ret != 0 or data is None or data.empty:
            break
        closes.extend(data["close"].tolist())
        if page_key is None:
            break
    closes.reverse()   # oldest first
    return closes


def analyze_timeframe(ctx, code: str, subtype: ft.SubType,
                      period_rsi: int = 14) -> dict:
    """Compute RSI + MACD for one timeframe. Returns {} if insufficient data."""
    closes = fetch_closes(ctx, code, subtype)
    if len(closes) < 35:
        return {}
    rsi = compute_rsi(closes, period_rsi)
    macd = compute_macd(closes)
    return {"rsi": rsi, "macd": macd, "n": len(closes)}


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    stocks = [
        "HK.00700", "HK.09988", "HK.00388", "HK.00941",
        "HK.02318", "HK.01658", "HK.06888", "HK.02628",
    ]

    ctx = create_quote_context()

    # Timeframe configs
    TIMEFRAMES = [
        ("Daily",   ft.SubType.K_DAY,  14),
        ("60M",     ft.SubType.K_60M,  14),
        ("15M",     ft.SubType.K_15M,  10),
    ]

    print(f"Fetching multi-timeframe data for {len(stocks)} stocks...\n")

    results = {}
    for stock in stocks:
        tf_data = {}
        for label, subtype, rsi_period in TIMEFRAMES:
            data = analyze_timeframe(ctx, stock, subtype)
            tf_data[label] = data

        rsi_d  = tf_data.get("Daily", {}).get("rsi", 50)
        rsi_60 = tf_data.get("60M",   {}).get("rsi", 50)
        rsi_15 = tf_data.get("15M",   {}).get("rsi", 50)
        macd_d = tf_data.get("Daily", {}).get("macd", 0)
        n_d    = tf_data.get("Daily", {}).get("n",    0)
        n_60   = tf_data.get("60M",   {}).get("n",    0)
        n_15   = tf_data.get("15M",   {}).get("n",    0)

        # Signal logic
        buy_score  = sum(1 for r in [rsi_d, rsi_60, rsi_15] if r < 40)
        sell_score = sum(1 for r in [rsi_d, rsi_60, rsi_15] if r > 60)
        triple_buy  = buy_score  >= 3 and macd_d > 0
        triple_sell = sell_score >= 3 and macd_d < 0
        double_buy  = buy_score  >= 2
        double_sell = sell_score >= 2

        if triple_buy:
            badge = "⬤ TRIPLE BUY"
        elif triple_sell:
            badge = "○ TRIPLE SELL"
        elif double_buy:
            badge = "◐ DOUBLE BUY"
        elif double_sell:
            badge = "◑ DOUBLE SELL"
        elif buy_score >= 1:
            badge = "◐  WATCH"
        elif sell_score >= 1:
            badge = "◑  WATCH"
        else:
            badge = "●  neutral"

        results[stock] = {
            "rsi_d": rsi_d, "rsi_60": rsi_60, "rsi_15": rsi_15,
            "macd_d": macd_d,
            "badge": badge,
            "conviction": buy_score if buy_score >= 2 else -sell_score if sell_score >= 2 else 0,
            "n_d": n_d, "n_60": n_60, "n_15": n_15,
        }

    ctx.close()

    # ── Print ──────────────────────────────────────────────────────────────

    header = (f"  {'Stock':<12} {'Daily':>7} {'60M':>7} {'15M':>7}  "
              f"{'MACD(D)':>10}  {'Signal':<16}  {'Candles'}")
    print(header)
    print("  " + "-" * 90)

    sorted_stocks = sorted(
        results.keys(),
        key=lambda s: results[s]["conviction"],
        reverse=True
    )

    for stock in sorted_stocks:
        r = results[stock]
        ok = lambda n: f"({n})" if n else "(?)"
        print(f"  {stock:<12} {r['rsi_d']:>7.1f} {r['rsi_60']:>7.1f} "
              f"{r['rsi_15']:>7.1f}  {r['macd_d']:>+10.4f}  "
              f"{r['badge']:<16}  "
              f"D={r['n_d']} 60M={r['n_60']} 15M={r['n_15']}")

    print()
    top_buy = [s for s in sorted_stocks if results[s]["conviction"] > 0]
    if top_buy:
        print(f"Top conviction BUY candidates: {', '.join(top_buy)}")
    else:
        print("No high-conviction signals this run.")


if __name__ == "__main__":
    main()
