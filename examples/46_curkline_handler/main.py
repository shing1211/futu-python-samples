#!/usr/bin/env python3
"""
46 — CurKline Handler

CurKlineHandlerBase streams real-time candlestick updates as they build up.
Unlike request_history_kline which gives you closed candles,
this handler gives you the LIVE candle as it forms -- every tick
that moves the open/high/low/close/vol.

Useful for:
  - Real-time MACD/strategy signals without polling
  - Intraday candlestick pattern recognition
  - Live chart rendering

SDK: OpenQuoteContext.set_handler() + CurKlineHandlerBase
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
import futu as ft
from connect import create_quote_context


class MyCurKlineHandler(ft.CurKlineHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, content = super().on_recv_rsp(rsp_pb)
        if ret_code != ft.RET_OK:
            return ft.RET_ERROR, content

        # content is a DataFrame with K-line fields:
        # code, kline_type, open, high, low, close, volume, turnover, ...
        for _, row in content.iterrows():
            code   = row.get("code", "?")
            ktype  = row.get("kline_type", "?")
            open_  = row.get("open", 0)
            high   = row.get("high", 0)
            low    = row.get("low", 0)
            close  = row.get("close", 0)
            vol    = row.get("volume", 0)
            turn   = row.get("turnover", 0)
            ts     = row.get("time", "?") if "time" in row else "?"

            print(f"  [{code}] {ktype} | {ts} | "
                  f"O={float(open_):.2f} H={float(high):.2f} "
                  f"L={float(low):.2f} C={float(close):.2f} "
                  f"| vol={int(vol):,} turn={float(turn):,.0f}")

        return ft.RET_OK, content


def main():
    ctx = create_quote_context()
    try:
        ctx.set_handler(MyCurKlineHandler())
    
        stock = "HK.00700"
        # Subscribe to daily K-line push (K_DAY = current day's candle)
        ret, _ = ctx.subscribe(stock, ft.SubType.K_DAY)
        if ret != 0:
            print(f"Subscribe failed: {ret}")
            return
    
        print(f"Subscribed to {stock} K_DAY push (today's live candle).")
        print("Each push = one updated candle as it forms.\n")
    
        print("Waiting 20s for candle updates (press Ctrl+C to exit)...\n")
        time.sleep(20)
    
    finally:
        ctx.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
