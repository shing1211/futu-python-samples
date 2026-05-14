#!/usr/bin/env python3
"""
64 — Backtesting Mini-Framework

Pull historical K-line data, run a parameterized strategy, and compute
performance metrics. No live trading — pure historical analysis.

Built-in strategies:
  - SmaCross: short MA crosses above/below long MA
  - RsiStrategy: RSI < oversold buy, > overbought sell
  - MacdStrategy: golden cross / death cross

SDK: OpenQuoteContext.request_history_kline() (paginated)
                .get_history_kl_quota()
"""

import sys
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
import futu as ft
from connect import create_quote_context
from engine import backtest
from strategies import SmaCross, RsiStrategy, MacdStrategy

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

STOCK = "HK.00700"
START = "2024-01-01"
END = "2026-05-14"
KTYPE = ft.KLType.K_DAY
AUTYPE = ft.AuType.QFQ
INITIAL_CAPITAL = 1_000_000


def fetch_klines(ctx):
    ret, quota = ctx.get_history_kl_quota()
    if ret == ft.RET_OK:
        if isinstance(quota, tuple) and len(quota) >= 2:
            remain = quota[1]
            if isinstance(remain, (int, float)) and remain < 50:
                print(f"  WARNING: K-line quota low ({remain} remaining)")
    page_key = None
    all_data = []
    while True:
        ret, data, page_key = ctx.request_history_kline(
            STOCK, start=START, end=END, ktype=KTYPE,
            autype=AUTYPE, max_count=1000, page_req_key=page_key,
        )
        if ret != 0:
            print(f"  request_history_kline failed: {data}")
            return None
        all_data.append(data)
        if page_key is None:
            break
    import pandas as pd
    df = pd.concat(all_data, ignore_index=True) if len(all_data) > 1 else all_data[0]
    return df


def print_results(strategy, metrics, trades):
    print(f"\n  === {strategy.description} ===")
    print(f"  Stock: {STOCK}")
    print(f"  Period: {START} → {END}\n")
    print(f"  Initial Capital: {INITIAL_CAPITAL:,.0f}")
    print(f"  Final Capital:   {metrics['final_capital']:,.0f}")
    print(f"  Total Return:    {metrics['total_return_pct']:+.2f}%")
    print(f"  Sharpe Ratio:    {metrics['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown:    {metrics['max_drawdown_pct']:.2f}%")
    print(f"  Win Rate:        {metrics['win_rate_pct']:.1f}%")
    print(f"  Trades:          {metrics['num_trades']}\n")
    print(f"  Trade Log:")
    print(f"  {'Date':<14} {'Type':<6} {'Price':>10} {'Qty':>6} {'Cost/PNL':>12}")
    print(f"  {'-'*14} {'-'*6} {'-'*10} {'-'*6} {'-'*12}")
    for t in trades[:20]:
        pnl = t.get("pnl", t.get("cost", 0))
        val = f"{pnl:>+10,.0f}" if t["type"] in ("SELL", "CLOSE") else f"{pnl:>10,.0f}"
        print(f"  {t['date']:<14} {t['type']:<6} {t['price']:>10.2f} {t['qty']:>6} {val}")
    if len(trades) > 20:
        print(f"  ... {len(trades) - 20} more trades")


def main():
    print(f"  === Backtesting Mini-Framework ===\n")
    print(f"  Stock: {STOCK} | Period: {START} → {END}\n")

    ctx = create_quote_context()

    try:
        df = fetch_klines(ctx)
        if df is None or df.empty:
            print("  No data returned")
            return

        print(f"  Fetched {len(df)} bars ({df['time_key'].min()} → {df['time_key'].max()})\n")

        strategies = [
            SmaCross(short=50, long=200),
            RsiStrategy(period=14, oversold=30, overbought=70),
            MacdStrategy(fast=12, slow=26, signal=9),
        ]

        for strategy in strategies:
            metrics, trades, _ = backtest(df, strategy, INITIAL_CAPITAL)
            print_results(strategy, metrics, trades)
            print()

    finally:
        ctx.close()


if __name__ == "__main__":
    main()
