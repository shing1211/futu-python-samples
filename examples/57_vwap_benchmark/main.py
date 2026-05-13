#!/usr/bin/env python3
"""
57 — VWAP Benchmark

Subscribes to the TICKER push stream and accumulates a running
Volume-Weighted Average Price (VWAP) in real time.

VWAP is the gold standard for execution quality:
  - If you bought above VWAP → poor execution (adverse selection)
  - If you bought below VWAP → good execution (price improvement)

The script also tracks:
  - Cumulative turnover
  - VWAP deviation: how far the current price is from VWAP
  - A simulated "entry" at the first tick price, and marks
    P&L vs VWAP at each subsequent tick

What you'll see:
  Every 30 seconds: cumulative stats and current position vs VWAP.
  After the full window: final summary with entry/exit stats.

SDK: OpenQuoteContext + TickerHandlerBase + TICKER subtype
"""

import sys
import time
from pathlib import Path

# Resolve repo root once, add to sys.path
_REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Unbuffered stdout — print() calls reach terminal immediately
sys.stdout.reconfigure(line_buffering=True)

import futu as ft
from examples.connect import create_quote_context


# ── VWAP accumulator ────────────────────────────────────────────────────────

class VWAPAccumulator:
    """
    Accumulates price × volume across ticker prints to compute running VWAP.

    VWAP = Σ(price_i × vol_i) / Σ(vol_i)
    """

    def __init__(self):
        self.prices:    list[float] = []
        self.volumes:   list[float] = []
        self.timestamps: list[str]  = []

        self.sum_pv:     float = 0.0   # Σ(price × volume in HKD)
        self.sum_vol:    float = 0.0   # Σ(volume in shares)
        self.tick_count: int   = 0
        self.start_ts:   float | None = None
        self.entry_price: float | None = None
        self.max_price:  float = 0.0
        self.min_price:  float = float("inf")

    def update(self, price: float, volume: float, turnover: float, ts: str):
        """ticker: price/share, volume/shares, turnover/HKD."""
        if self.start_ts is None:
            self.start_ts = time.time()
            self.entry_price = price

        self.prices.append(price)
        self.volumes.append(volume)
        self.timestamps.append(ts)
        self.sum_pv  += turnover
        self.sum_vol += volume
        self.tick_count += 1

        if price > self.max_price:
            self.max_price = price
        if price < self.min_price:
            self.min_price = price

    @property
    def vwap(self) -> float:
        return self.sum_pv / self.sum_vol if self.sum_vol else 0.0

    @property
    def last_price(self) -> float:
        return self.prices[-1] if self.prices else 0.0

    @property
    def elapsed_s(self) -> float:
        return time.time() - self.start_ts if self.start_ts else 0.0

    def deviation_bps(self) -> float:
        vp = self.vwap
        lp = self.last_price
        if vp == 0 or lp == 0:
            return 0.0
        return ((lp - vp) / vp) * 10_000

    def pnl_bps(self) -> float:
        ep = self.entry_price
        vp = self.vwap
        if ep is None or vp == 0:
            return 0.0
        return ((self.last_price - vp) / vp) * 10_000

    def mini_report(self):
        elapsed = self.elapsed_s
        last    = self.last_price
        vwap    = self.vwap
        dev     = self.deviation_bps()
        pnl     = self.pnl_bps()
        spread  = self.max_price - self.min_price
        turnover = int(self.sum_pv)

        dev_str = f"{dev:+.1f}bps" if dev else "N/A"
        pnl_str = f"{pnl:+.1f}bps" if pnl else "N/A"

        print(f"  [{elapsed:>5.0f}s | tick={self.tick_count:>4}] "
              f"price={last:>9.3f}  VWAP={vwap:>9.3f}  "
              f"dev={dev_str}  P&L={pnl_str}  "
              f"HKD={turnover:>13,}  range={spread:.3f}")


# ── Ticker handler ──────────────────────────────────────────────────────────

class VWAPTickerHandler(ft.TickerHandlerBase):
    """
    Each on_recv_rsp call is one ticker event — a single trade print.
    We accumulate it into the VWAP accumulator.
    """

    def __init__(self, accumulator: VWAPAccumulator):
        super().__init__()
        self.accumulator = accumulator

    def on_recv_rsp(self, rsp_pb) -> tuple:
        ret_code, content = super().on_recv_rsp(rsp_pb)
        if ret_code != ft.RET_OK:
            return ft.RET_ERROR, content

        # Use hasattr — isinstance(content, pd.DataFrame) can be False
        # due to module isolation even when content IS a DataFrame.
        if not hasattr(content, "iterrows"):
            return ft.RET_OK, content

        for _, row in content.iterrows():
            self.accumulator.update(
                price    = float(row.get("price", 0)),
                volume   = float(row.get("volume", 0)),
                turnover = float(row.get("turnover", 0)),
                ts       = str(row.get("time", "")),
            )

        return ft.RET_OK, content


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    stock        = "HK.00700"
    DURATION_SEC = 300        # 5-minute run
    REPORT_EVERY = 30         # print a line every 30s

    ctx = create_quote_context()
    vwap_acc = VWAPAccumulator()
    ctx.set_handler(VWAPTickerHandler(vwap_acc))

    print(f"Stock  : {stock}")
    print(f"Window : {DURATION_SEC}s")
    print(f"Reports: every {REPORT_EVERY}s\n")
    print(f"  {'Time':>7}  {'Price':>9}  {'VWAP':>9}  {'Dev':>9}  "
          f"{'P&L':>9}  {'Turnover (HKD)':>16}  {'Range':>6}")
    print(f"  {'-'*7}  {'-'*9}  {'-'*9}  {'-'*9}  "
          f"{'-'*9}  {'-'*16}  {'-'*6}")

    ret, _ = ctx.subscribe(stock, ft.SubType.TICKER)
    if ret != 0:
        print(f"Subscribe failed: {ret}")
        ctx.close()
        return

    print("Collecting ticks...\n")

    start      = time.time()
    last_report = start
    try:
        while time.time() - start < DURATION_SEC:
            time.sleep(1)
            if time.time() - last_report >= REPORT_EVERY:
                if vwap_acc.tick_count > 0:
                    vwap_acc.mini_report()
                else:
                    print(f"  [{vwap_acc.elapsed_s:.0f}s] waiting for ticks...")
                last_report = time.time()
    except KeyboardInterrupt:
        pass

    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    if vwap_acc.tick_count == 0:
        print("No ticker data received.")
    else:
        vwap_acc.mini_report()
        print()
        entry = vwap_acc.entry_price
        last  = vwap_acc.last_price
        vwap  = vwap_acc.vwap
        print(f"  Entry price : {entry:.3f}")
        print(f"  Final price : {last:.3f}")
        print(f"  VWAP        : {vwap:.3f}")
        print(f"  High        : {vwap_acc.max_price:.3f}")
        print(f"  Low         : {vwap_acc.min_price:.3f}")
        print(f"  Total ticks : {vwap_acc.tick_count}")
        print(f"  Total HKD   : {int(vwap_acc.sum_pv):,}")
        dev = ((last - vwap) / vwap * 10_000) if vwap else 0
        print(f"  Dev from VWAP: {dev:+.1f}bps")
        if entry:
            pnl = ((last - entry) / entry * 10_000)
            print(f"  P&L vs entry : {pnl:+.1f}bps ({pnl/100:.2f}%)")

    ctx.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
