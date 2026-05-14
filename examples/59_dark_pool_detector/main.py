#!/usr/bin/env python3
"""
59 — Dark Pool / Block Trade Detector

Cross-reference ticker prints against broker queue depth. When a large
ticker print occurs without a corresponding reduction in the broker queue
at that price level, flag it as a potential dark pool / off-book trade.

SDK: OpenQuoteContext.subscribe(TICKER, BROKER)
               .get_order_book()  (fallback)
    TickerHandlerBase + BrokerHandlerBase
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

STOCK = "HK.00700"
BLOCK_THRESHOLD_LOTS = 10
DURATION_SEC = 120


class BrokerSnapshot:
    def __init__(self):
        self.bid_levels: list = []
        self.ask_levels: list = []
        self.updated_at: float = 0

    def update(self, bid: list, ask: list):
        self.bid_levels = bid
        self.ask_levels = ask
        self.updated_at = time.time()


class TickerAccumulator:
    def __init__(self):
        self.pending: dict[float, int] = {}

    def add(self, price: float, volume: int):
        self.pending[price] = self.pending.get(price, 0) + volume

    def flush(self) -> list[tuple[float, int]]:
        items = list(self.pending.items())
        self.pending.clear()
        return items


def find_volume_at_price(levels: list, price: float, tolerance: float = 0.01) -> int:
    for level in levels:
        if len(level) >= 2:
            level_price = float(level[0])
            if abs(level_price - price) / max(level_price, 0.01) < tolerance:
                return int(level[1])
    return 0


class DetectionHandler(ft.TickerHandlerBase):
    def __init__(self, broker: BrokerSnapshot, acc: TickerAccumulator):
        super().__init__()
        self.broker = broker
        self.acc = acc
        self.block_count = 0

    def on_recv_rsp(self, rsp_pb):
        ret_code, content = super().on_recv_rsp(rsp_pb)
        if ret_code != ft.RET_OK:
            return ft.RET_ERROR, content
        if not hasattr(content, "iterrows"):
            return ft.RET_OK, content

        for _, row in content.iterrows():
            price = float(row.get("price", 0))
            volume = int(row.get("volume", 0))
            if volume >= BLOCK_THRESHOLD_LOTS:
                self.acc.add(price, volume)

        for price, vol in self.acc.flush():
            if time.time() - self.broker.updated_at < 5:
                bid_vol = find_volume_at_price(self.broker.bid_levels, price)
                ask_vol = find_volume_at_price(self.broker.ask_levels, price)
                queue_vol = max(bid_vol, ask_vol)
                expected_drop = vol
                actual_drop = queue_vol
                if abs(expected_drop - actual_drop) > expected_drop * 0.5:
                    self.block_count += 1
                    print(f"  ⬤ BLOCK #{self.block_count}: price={price:.2f} "
                          f"vol={vol} queue_drop={actual_drop} expected={expected_drop} "
                          f"(potential dark pool)")
            else:
                print(f"  ◐ LARGE TRADE: price={price:.2f} vol={vol} "
                      f"(no broker queue data — insufficient permissions?)")

        return ft.RET_OK, content


class BrokerHandler(ft.BrokerHandlerBase):
    def __init__(self, snapshot: BrokerSnapshot):
        super().__init__()
        self.snapshot = snapshot

    def on_recv_rsp(self, rsp_pb):
        ret_code, stock_code, contents = super().on_recv_rsp(rsp_pb)
        if ret_code == ft.RET_OK:
            bid_content, ask_content = contents[0], contents[1]
            bid_levels = bid_content.to_dict("records") if hasattr(bid_content, "to_dict") else bid_content
            ask_levels = ask_content.to_dict("records") if hasattr(ask_content, "to_dict") else ask_content
            self.snapshot.update(bid_levels, ask_levels)
        return ret_code


def main():
    print(f"  === Dark Pool / Block Trade Detector ===\n")
    print(f"  Stock: {STOCK}")
    print(f"  Block threshold: {BLOCK_THRESHOLD_LOTS} lots")
    print(f"  Duration: {DURATION_SEC}s\n")
    print(f"  A large ticker print that does NOT reduce broker")
    print(f"  queue volume at the same price suggests off-book execution.\n")

    ctx = create_quote_context()
    snapshot = BrokerSnapshot()
    acc = TickerAccumulator()

    ctx.set_handler(DetectionHandler(snapshot, acc))
    ctx.set_handler(BrokerHandler(snapshot))

    ret, _ = ctx.subscribe(STOCK, [ft.SubType.TICKER, ft.SubType.BROKER])
    if ret != 0:
        print(f"  Subscribe failed: {ret}")
        ctx.close()
        return

    print(f"  Listening for {DURATION_SEC}s...\n")

    try:
        time.sleep(DURATION_SEC)
    except KeyboardInterrupt:
        pass
    finally:
        print(f"\n  Block trades detected: {acc.__class__.__name__}")
        ctx.close()


if __name__ == "__main__":
    main()
