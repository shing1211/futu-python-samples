# -*- coding: utf-8 -*-

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

"""预测市场·事件合约实时行情 (Prediction Market · Event Contract Real-Time)

Demonstrates the SDK 10.9.6908 event contract real-time surface:
  - subscribe_event_contract:          subscribe QUOTE/ORDER_BOOK/TICKER/K_DAY
  - EventContractOrderBookHandlerBase: order book push callback
  - EventContractKlineHandlerBase:     K-line push callback
  - EventContractTickerHandlerBase:    ticker push callback
  - get_event_contract_snapshot:       YES/NO last price, bid/ask, cumulative volume
  - get_event_contract_order_book:     multi-level YES/NO depth (dict of tuples)
  - get_event_contract_kline:          contract-level K-line (PredSide YES/NO)
  - get_event_contract_ticker:         recent tick-by-tick prints
  - request_history_event_contract_kline: historical K-line (no download needed)
  - unsubscribe_event_contract / unsubscribe_all_event_contract

Requires OpenD 10.9.6908+ and Prediction Market quote permission.
"""

import logging
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

PUSH_SECONDS = 3


class EventContractOrderBookLog(ft.EventContractOrderBookHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret, content = super().on_recv_rsp(rsp_pb)
        if ret != ft.RET_OK:
            logger.warning("  [push] order book error: %s", content)
            return ret, content
        for item in content[:2]:
            logger.info("  [push] order book %s: YES bid=%.4f/ask=%.4f  NO bid=%.4f/ask=%.4f",
                        item.get("code", "?"),
                        item.get("yes_bids", [(0, 0)])[0][0], item.get("yes_asks", [(0, 0)])[0][0],
                        item.get("no_bids", [(0, 0)])[0][0], item.get("no_asks", [(0, 0)])[0][0])
        return ret, content


class EventContractKlineLog(ft.EventContractKlineHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret, content = super().on_recv_rsp(rsp_pb)
        if ret != ft.RET_OK:
            logger.warning("  [push] kline error: %s", content)
            return ret, content
        if content is not None and not content.empty:
            last = content.iloc[-1]
            logger.info("  [push] kline %s %s close=%.4f vol=%s",
                        last.get("code", "?"), last.get("time_key", "?"),
                        last.get("close", 0.0), last.get("volume", "?"))
        return ret, content


class EventContractTickerLog(ft.EventContractTickerHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret, content = super().on_recv_rsp(rsp_pb)
        if ret != ft.RET_OK:
            logger.warning("  [push] ticker error: %s", content)
            return ret, content
        if content is not None and not content.empty:
            last = content.iloc[-1]
            logger.info("  [push] ticker %s time=%s yes=%.4f no=%.4f vol=%s",
                        last.get("code", "?"), last.get("time", "?"),
                        last.get("yes_price", 0.0), last.get("no_price", 0.0),
                        last.get("volume", "?"))
        return ret, content


def find_first_contract(ctx):
    """Navigate category → series → event → contract; return first contract code."""
    ret, series = ctx.get_event_contract_series_list(category="SPORTS")
    if ret != ft.RET_OK or series is None or series.empty:
        logger.warning("  no Sports series available: %s", series)
        return None
    series_code = series.iloc[0].get("series_code")
    ret, events, _ = ctx.get_event_contract_event_list(series_code, count=5)
    if ret != ft.RET_OK or events is None or events.empty:
        logger.warning("  no events under %s: %s", series_code, events)
        return None
    event_code = events.iloc[0].get("event_code")
    ret, cont, _ = ctx.get_event_contract(event_code, count=10)
    if ret != ft.RET_OK:
        logger.warning("  get_event_contract failed: %s", cont)
        return None
    contracts = cont.get("contract_list") if isinstance(cont, dict) else None
    if contracts is None or contracts.empty:
        logger.warning("  no contracts under %s", event_code)
        return None
    return contracts.iloc[0].get("contract_code")


if __name__ == "__main__":
    logger.info("=== Prediction Market · Event Contract Real-Time (SDK 10.9.6908+) ===\n")

    ctx = create_quote_context()
    try:
        code = find_first_contract(ctx)
        if code is None:
            logger.warning("No event contract discovered — check OpenD 10.9.6908+ and "
                           "Prediction Market quote permission.")
            sys.exit(0)
        logger.info("Using contract: %s\n", code)

        # Register push handlers before subscribing
        ctx.set_handler(EventContractOrderBookLog())
        ctx.set_handler(EventContractKlineLog())
        ctx.set_handler(EventContractTickerLog())

        # Subscribe to real-time feeds
        subtype_list = [ft.SubType.QUOTE, ft.SubType.ORDER_BOOK,
                        ft.SubType.TICKER, ft.SubType.K_DAY]
        ret, msg = ctx.subscribe_event_contract([code], subtype_list, is_first_push=True)
        if ret != ft.RET_OK:
            logger.warning("subscribe_event_contract failed: %s", msg)
        else:
            logger.info("Subscribed %s -> %s\n", code, subtype_list)
            logger.info("Listening for pushes %d seconds...", PUSH_SECONDS)
            time.sleep(PUSH_SECONDS)
        print("")

        # Pull-style real-time reads
        ret, snap = ctx.get_event_contract_snapshot([code])
        if ret != ft.RET_OK:
            logger.warning("snapshot failed: %s", snap)
        else:
            row = snap.iloc[0]
            logger.info("── Snapshot %s ──", code)
            logger.info("  name=%-30s price=%-6s volume=%-8s status=%s",
                        row.get("name", "?"), row.get("price", "?"),
                        row.get("cumulative_volume", "?"), row.get("status", "?"))
            logger.info("  YES bid=%-6s sz=%s  ask=%-6s sz=%s",
                        row.get("yes_bid", "?"), row.get("yes_bid_size", "?"),
                        row.get("yes_ask", "?"), row.get("yes_ask_size", "?"))
            logger.info("  NO  bid=%-6s sz=%s  ask=%-6s sz=%s",
                        row.get("no_bid", "?"), row.get("no_bid_size", "?"),
                        row.get("no_ask", "?"), row.get("no_ask_size", "?"))
        print("")

        ret, ob = ctx.get_event_contract_order_book(code, num=5)
        if ret != ft.RET_OK:
            logger.warning("order book failed: %s", ob)
        else:
            logger.info("── Order book %s (top 3 of each side) ──", ob.get("code", code))
            for label, key in [("YES bid", "yes_bids"), ("YES ask", "yes_asks"),
                               ("NO bid", "no_bids"), ("NO ask", "no_asks")]:
                levels = ob.get(key, [])[:3]
                logger.info("  %-8s %s", label, levels)
        print("")

        ret, kline = ctx.get_event_contract_kline(code, pre_side=ft.PredSide.YES,
                                                  ktype=ft.KLType.K_DAY, max_count=5)
        if ret != ft.RET_OK:
            logger.warning("kline failed: %s", kline)
        elif kline is not None and not kline.empty:
            logger.info("── K-line (PredSide.YES, K_DAY) last 5 ──")
            for _, r in kline.iterrows():
                logger.info("  %s open=%.4f high=%.4f low=%.4f close=%.4f vol=%s",
                            r.get("time_key", "?"), r.get("open", 0.0), r.get("high", 0.0),
                            r.get("low", 0.0), r.get("close", 0.0), r.get("volume", "?"))
        print("")

        ret, tick = ctx.get_event_contract_ticker(code, count=5)
        if ret != ft.RET_OK:
            logger.warning("ticker failed: %s", tick)
        elif tick is not None and not tick.empty:
            logger.info("── Recent ticker (5) ──")
            for _, r in tick.iterrows():
                logger.info("  %s yes=%.4f no=%.4f vol=%s side=%s",
                            r.get("time", "?"), r.get("yes_price", 0.0),
                            r.get("no_price", 0.0), r.get("volume", "?"), r.get("side", "?"))
        print("")

        ret, hist = ctx.request_history_event_contract_kline(
            code, start="2026-06-01", end="2026-08-01",
            pre_side=ft.PredSide.YES, ktype=ft.KLType.K_DAY, max_count=5)
        if ret != ft.RET_OK:
            logger.warning("history kline failed: %s", hist)
        elif hist is not None and not hist.empty:
            logger.info("── History K-line (last 5) ──")
            for _, r in hist.iterrows():
                logger.info("  %s close=%.4f vol=%s",
                            r.get("time_key", "?"), r.get("close", 0.0), r.get("volume", "?"))
        print("")

        # Clean up subscriptions
        ret, msg = ctx.unsubscribe_event_contract([code], subtype_list)
        if ret != ft.RET_OK:
            logger.warning("unsubscribe_event_contract: %s", msg)
        else:
            logger.info("Unsubscribed %s by code/type", code)
        ret, msg = ctx.unsubscribe_all_event_contract()
        if ret != ft.RET_OK:
            logger.warning("unsubscribe_all_event_contract: %s", msg)
        else:
            logger.info("unsubscribe_all_event_contract OK")
    finally:
        ctx.close()

    print("\nDone.")
