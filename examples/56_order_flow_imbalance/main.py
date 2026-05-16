#!/usr/bin/env python3
"""
56 — Order Flow Imbalance

Tracks the ORDER_BOOK push stream and accumulates the delta in bid
and ask quantity at each level between consecutive snapshots.

The accumulated delta is the Order Flow Imbalance (OFI) — a measure
of which side is more aggressive.  A sustained positive OFI means
buy pressure is dominant; negative means sell pressure is dominant.

After collecting for N minutes, the script prints:
  - Bid OFI vs Ask OFI per level
  - Net OFI (bid total - ask total)
  - Cumulative OFI over time
  - Signal: which side is in control

What you'll see:
  Every 30 seconds: a mini-report of OFI accumulation so far.
  After the full window: a final summary with the signal.

SDK: OpenQuoteContext + OrderBookHandlerBase + ORDER_BOOK subtype
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
import futu as ft
from connect import create_quote_context


# ── OFI accumulator ─────────────────────────────────────────────────────────

class OFIAccumulator:
    """
    Order Flow Imbalance: accumulates the change in quantity at each
    price level between ORDER_BOOK snapshots.

    BidOFI  > 0  → more buy aggression (quantity added/removed on bid)
    AskOFI  < 0  → more sell aggression
    """

    def __init__(self, num_levels: int = 5):
        self.num_levels = num_levels
        self.prev_bid: list[float] = []
        self.prev_ask: list[float] = []
        self.bid_ofi:  list[float] = [0.0] * num_levels
        self.ask_ofi:  list[float] = [0.0] * num_levels
        self.cumulative_bid: float = 0.0
        self.cumulative_ask: float = 0.0
        self.tick_count: int = 0
        self.start_time: float | None = None

    def update(self, bid_levels: list, ask_levels: list):
        """
        bid_levels / ask_levels: list of 4-tuples (price, vol, count, {}).
        We track the cumulative volume at each level.
        """
        def to_float(v):
            return float(v) if v is not None else 0.0

        def get_price_level(levels, i):
            return to_float(levels[i][0]) if i < len(levels) else 0.0

        def get_vol_level(levels, i):
            return to_float(levels[i][1]) if i < len(levels) else 0.0

        if self.start_time is None:
            self.start_time = time.time()
            self.prev_bid = [get_vol_level(bid_levels, i) for i in range(self.num_levels)]
            self.prev_ask = [get_vol_level(ask_levels, i) for i in range(self.num_levels)]
            return

        cur_bid = [get_vol_level(bid_levels, i) for i in range(self.num_levels)]
        cur_ask = [get_vol_level(ask_levels, i) for i in range(self.num_levels)]

        for i in range(self.num_levels):
            bid_delta = cur_bid[i] - self.prev_bid[i]
            ask_delta = cur_ask[i] - self.prev_ask[i]
            # Positive delta = more volume added at this level
            # Bids: taker hitting bid = buy aggression
            # Asks: taker lifting ask = sell aggression
            self.bid_ofi[i] += max(bid_delta, 0)
            self.ask_ofi[i] += max(ask_delta, 0)

        self.cumulative_bid = sum(self.bid_ofi)
        self.cumulative_ask = sum(self.ask_ofi)
        self.prev_bid = cur_bid
        self.prev_ask = cur_ask
        self.tick_count += 1

    @property
    def net_ofi(self) -> float:
        return self.cumulative_bid - self.cumulative_ask

    @property
    def elapsed_s(self) -> float:
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time

    def signal(self) -> str:
        ratio = self.net_ofi / (abs(self.cumulative_bid) + abs(self.cumulative_ask) + 1)
        if ratio > 0.15:
            return "🟢 BUY pressure"
        elif ratio < -0.15:
            return "🔴 SELL pressure"
        elif ratio > 0.05:
            return "🟡 mild BUY"
        elif ratio < -0.05:
            return "🟡 mild SELL"
        return "⚪ balanced"

    def mini_report(self):
        elapsed = self.elapsed_s
        print(f"\n  [{elapsed:.0f}s | {self.tick_count} snapshots]")
        print(f"  {'Level':<8} {'BidOFI':>14}  {'AskOFI':>14}  {'Price(Bid)':>12}")
        print(f"  {'-'*8} {'-'*14}  {'-'*14}  {'-'*12}")
        for i in range(self.num_levels):
            print(f"  {i+1:<8} {self.bid_ofi[i]:>14,.0f}  {self.ask_ofi[i]:>+14,.0f}")

        print(f"\n  Net OFI : {self.net_ofi:>+14,.0f}")
        print(f"  Cum Bid : {self.cumulative_bid:>14,.0f}")
        print(f"  Cum Ask : {self.cumulative_ask:>14,.0f}")
        print(f"  Signal  : {self.signal()}")


# ── ORDER_BOOK handler ──────────────────────────────────────────────────────

class OFIHandler(ft.OrderBookHandlerBase):
    """Fires on every ORDER_BOOK push and feeds it into the OFI accumulator."""

    def __init__(self, accumulator: OFIAccumulator):
        super().__init__()
        self.accumulator = accumulator

    def on_recv_rsp(self, rsp_pb) -> tuple:
        ret_code, content = super().on_recv_rsp(rsp_pb)
        if ret_code != ft.RET_OK:
            return ft.RET_ERROR, content

        # content is a dict with 'Bid' and 'Ask' keys (each a list of level dicts)
        if not isinstance(content, dict):
            return ft.RET_OK, content

        bid_levels = content.get("Bid", [])
        ask_levels = content.get("Ask", [])

        if bid_levels and ask_levels:
            self.accumulator.update(bid_levels, ask_levels)

        return ft.RET_OK, content


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    stock = "HK.00700"
    DURATION_SEC = 300      # collect OFI for 5 minutes
    REPORT_EVERY_SEC = 30   # print a mini-report every 30s

    ctx = create_quote_context()
    accumulator = OFIAccumulator(num_levels=5)
    ctx.set_handler(OFIHandler(accumulator))

    print(f"Stock  : {stock}")
    print(f"Window : {DURATION_SEC}s")
    print(f"Reports: every {REPORT_EVERY_SEC}s\n")

    ret, _ = ctx.subscribe(stock, ft.SubType.ORDER_BOOK)
    if ret != 0:
        print(f"Subscribe failed: {ret}")
        return

    print("Collecting order flow... (press Ctrl+C to stop early)\n")

    start = time.time()
    last_report = start
    try:
        while time.time() - start < DURATION_SEC:
            time.sleep(1)
            if time.time() - last_report >= REPORT_EVERY_SEC:
                accumulator.mini_report()
                last_report = time.time()
    except KeyboardInterrupt:
        pass
    finally:
        ctx.close()

    print("\n" + "=" * 50)
    print("FINAL SUMMARY")
    print("=" * 50)
    accumulator.mini_report()

    print("\nDone.")
