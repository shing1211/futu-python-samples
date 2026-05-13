#!/usr/bin/env python3
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
    ctx.set_handler(MyTickerHandler())

    stock = "HK.00700"
    print(f"Subscribing to {stock} TICKER stream...\n")
    print("Format: timestamp | code | direction | price | volume | type\n")

    ret, _ = ctx.subscribe(stock, ft.SubType.TICKER)
    if ret != 0:
        print(f"Subscribe failed: {ret}")
        ctx.close()
        return

    print("Waiting 15s for ticker prints (press Ctrl+C to exit)...\n")
    time.sleep(15)

    ctx.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
