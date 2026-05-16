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
45b — Ticker Handler

TickerHandlerBase catches every single trade print -- the raw,
microscopic heartbeat of the market. Each ticker event tells you:
  - price at which the trade happened
  - volume (number of lots)
  - direction (buy or sell vs the last trade)
  - time down to the millisecond

When volume spikes or price moves sharply, ticker data is where
you see it first -- before it shows up in a K-line or quote update.

SDK: OpenQuoteContext.set_handler() + TickerHandlerBase
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
import futu as ft
from connect import create_quote_context


class MyTickerHandler(ft.TickerHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, content = super().on_recv_rsp(rsp_pb)
        if ret_code != ft.RET_OK:
            return ft.RET_ERROR, content

        # content is a DataFrame with columns:
        # code, name, time, price, volume, direction, ticker_type, ...
        for _, row in content.iterrows():
            ts        = row.get("time", "?")
            code      = row.get("code", "?")
            price     = row.get("price", "?")
            vol       = row.get("volume", "?")
            direction = row.get("direction", "?")
            tick_type = row.get("type", "?")

            dir_str = "BUY" if str(direction) == "1" else "SELL"
            print(f"  {ts} | {code} | {dir_str:4s} | price={price} | vol={vol} | {tick_type}")

        return ft.RET_OK, content


def main():
    ctx = create_quote_context()
    try:
        ctx.set_handler(MyTickerHandler())
    
        stock = "HK.00700"
        print(f"Subscribing to {stock} TICKER stream...\n")
        print("Format: timestamp | code | direction | price | volume | type\n")
    
        ret, _ = ctx.subscribe(stock, ft.SubType.TICKER)
        if ret != 0:
            print(f"Subscribe failed: {ret}")
            return
    
        print("Waiting 15s for ticker prints (press Ctrl+C to exit)...\n")
        time.sleep(15)
    
    finally:
        ctx.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
