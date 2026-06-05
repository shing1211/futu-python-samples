#!/usr/bin/env python3

# Copyright (c) 2026 shing1211
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
117 — Odd-Lot Order Book Scanner

Subscribe to odd-lot order book data and compare with normal (round-lot)
order books. Demonstrates the new SDK 10.7.6708 OrderBookType.ODD API.

No order placement — pure market data monitoring.

SDK (10.7.6708+): OpenQuoteContext.get_order_book(order_book_type=OrderBookType.ODD)
                                .subscribe(SubType.ORDER_BOOK_ODD)
"""

import sys
import time
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

STOCK = "US.NVDA"
ODD_LOT_STOCK = "SG.D05"  # DBS Group — SG market supports odd-lot order books


def print_order_book(label, data, max_levels=5):
    if data is None:
        print(f"    {label}: no data")
        return
    if isinstance(data, tuple):
        ret_code, data = data
        if ret_code != ft.RET_OK:
            print(f"    {label}: error — {data}")
            return

    bids = data.get("Bid", [])[:max_levels]
    asks = data.get("Ask", [])[:max_levels]
    name = data.get("name", label)
    svr_recv_time = data.get("svr_recv_time_bid", "") or data.get("svr_recv_time_ask", "")
    print(f"    {name} (server recv: {svr_recv_time})")
    print(f"      {'Bid Price':>10} {'Bid Vol':>10} {'Orders':>8}   |  "
          f"{'Ask Price':>10} {'Ask Vol':>10} {'Orders':>8}")
    print(f"      {'-'*10} {'-'*10} {'-'*8}   |  "
          f"{'-'*10} {'-'*10} {'-'*8}")

    max_len = max(len(bids), len(asks))
    for i in range(max_len):
        bid_str = ""
        ask_str = ""
        if i < len(bids):
            b = bids[i]
            if isinstance(b, tuple):
                bid_str = f"{b[0]:>10.2f} {b[1]:>10} {b[2]:>8}"
            else:
                bid_str = f"{'N/A':>10} {'N/A':>10} {'N/A':>8}"
        else:
            bid_str = f"{'':>10} {'':>10} {'':>8}"

        if i < len(asks):
            a = asks[i]
            if isinstance(a, tuple):
                ask_str = f"{a[0]:>10.2f} {a[1]:>10} {a[2]:>8}"
            else:
                ask_str = f"{'N/A':>10} {'N/A':>10} {'N/A':>8}"
        print(f"      {bid_str}   |  {ask_str}")
    print()


def main():
    print(f"  === Odd-Lot Order Book Scanner (SDK 10.7.6708+) ===\n")
    print(f"  Odd-lot order books require SG or MY market data rights.\n")
    print(f"  Demo stock: {STOCK}")
    print(f"  Odd-lot test: {ODD_LOT_STOCK} (SG.D05 — DBS Group)\n")

    ctx = create_quote_context()
    try:
        print(f"  Subscribing to QUOTE and ORDER_BOOK for {STOCK}...")
        ret_sub, msg = ctx.subscribe(STOCK, [ft.SubType.QUOTE, ft.SubType.ORDER_BOOK])
        if ret_sub != ft.RET_OK:
            print(f"  Subscribe failed: {msg}")

        ret_sub2, msg2 = ctx.subscribe(
            ODD_LOT_STOCK, [ft.SubType.QUOTE, ft.SubType.ORDER_BOOK_ODD, ft.SubType.ORDER_BOOK],
        )
        odd_lot_available = ret_sub2 == ft.RET_OK
        if not odd_lot_available:
            print(f"  ORDER_BOOK_ODD subscription for {ODD_LOT_STOCK}: {msg2}")
            print(f"  (This is expected if your account does not have SG market data)\n")

        time.sleep(1)

        if odd_lot_available:
            print(f"  Round-lot order book ({ODD_LOT_STOCK}):")
            ret_n, normal_book = ctx.get_order_book(ODD_LOT_STOCK, num=5)
            if ret_n == ft.RET_OK:
                print_order_book("Normal (round-lot)", normal_book)
            else:
                print(f"    get_order_book failed: {normal_book}")

            print(f"  Odd-lot order book ({ODD_LOT_STOCK}):")
            ret_o, odd_book = ctx.get_order_book(ODD_LOT_STOCK, num=5, order_book_type=ft.OrderBookType.ODD)
            if ret_o == ft.RET_OK:
                print_order_book("Odd-lot", odd_book)
            else:
                print(f"    get_order_book(ODD) failed: {odd_book}")

            if ret_n == ft.RET_OK and ret_o == ft.RET_OK:
                norm_data = normal_book if isinstance(normal_book, dict) else None
                odd_data = odd_book if isinstance(odd_book, dict) else None
                if norm_data and odd_data:
                    norm_bid = [b for b in norm_data.get("Bid", []) if isinstance(b, tuple)]
                    norm_ask = [a for a in norm_data.get("Ask", []) if isinstance(a, tuple)]
                    odd_bid = [b for b in odd_data.get("Bid", []) if isinstance(b, tuple)]
                    odd_ask = [a for a in odd_data.get("Ask", []) if isinstance(a, tuple)]
                    print(f"  Comparison:")
                    if norm_bid and odd_bid:
                        print(f"    Best bid spread (round - odd): {norm_bid[0][0] - odd_bid[0][0]:.4f}")
                    if norm_ask and odd_ask:
                        print(f"    Best ask spread (round - odd): {norm_ask[0][0] - odd_ask[0][0]:.4f}")
                    print(f"    Round-lot bid depth: {sum(b[1] for b in norm_bid)}")
                    print(f"    Odd-lot bid depth:  {sum(b[1] for b in odd_bid)}")
        else:
            print(f"  Falling back to normal order book demonstration ({STOCK}):")
            ret_n, normal_book = ctx.get_order_book(STOCK, num=5)
            if ret_n == ft.RET_OK:
                print_order_book("Normal (round-lot)", normal_book)

        print(f"\n  Live quote monitoring for 15s...")

        class QuoteCountHandler(ft.StockQuoteHandlerBase):
            def __init__(self):
                super().__init__()
                self.count = 0

            def on_recv_rsp(self, rsp_pb):
                ret_code, content = super().on_recv_rsp(rsp_pb)
                if ret_code != ft.RET_OK:
                    return ft.RET_ERROR, content
                code = content.get("code", "?")
                price = content.get("last_price", 0)
                self.count += 1
                if self.count % 5 == 0:
                    print(f"    [{self.count}] {code}: {price:.2f}")
                return ft.RET_OK, content

        handler = QuoteCountHandler()
        ctx.set_handler(handler)

        deadline = time.time() + 15
        while time.time() < deadline:
            time.sleep(1)

        print(f"\n  Received {handler.count} quote updates.")

    except KeyboardInterrupt:
        print(f"\n  Stopped by user.")
    finally:
        ctx.close()
        print(f"  Done.")


if __name__ == "__main__":
    main()
