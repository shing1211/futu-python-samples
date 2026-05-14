# -*- coding: utf-8 -*-
"""实时行情推送 (StockQuoteHandlerBase / TickerHandlerBase / OrderBookHandlerBase / BrokerHandlerBase)

Demonstrates:
  - StockQuoteHandlerBase: real-time quote updates
  - TickerHandlerBase: tick-by-tick trade data
  - OrderBookHandlerBase: order book (bid/ask) depth updates
  - BrokerHandlerBase: broker queue (buy/sell wall) updates
  - set_handler: register multiple push handlers
  - subscribe: subscribe to multiple stock+subtype combos
  - Proper logging of all received fields

Note: opencode session may not show live push data in real-time.
Run the script directly to see continuous push updates.
"""
import logging
from time import sleep
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


class StockQuoteTest(ft.StockQuoteHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, content = super().on_recv_rsp(rsp_pb)
        if ret_code != ft.RET_OK:
            logger.debug("StockQuoteTest error: %s", content)
            return ft.RET_ERROR, content
        logger.info("[Quote] %s", content)
        return ft.RET_OK, content


class TickerTest(ft.TickerHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, content = super().on_recv_rsp(rsp_pb)
        if ret_code != ft.RET_OK:
            logger.error("TickerTest error: %s", content)
            return ft.RET_ERROR, content
        logger.info("[Ticker] code=%s price=%.2f vol=%d turnover=%.2f direction=%s",
                    content.get("code"), content.get("price"), content.get("volume"),
                    content.get("turnover"), content.get("direction"))
        return ft.RET_OK, content


class OrderBookTest(ft.OrderBookHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, content = super().on_recv_rsp(rsp_pb)
        if ret_code != ft.RET_OK:
            logger.error("OrderBookTest error: %s", content)
            return ft.RET_ERROR, content
        code = content.get("code", "?")
        bid = content.get("Bid", [])
        ask = content.get("Ask", [])
        logger.info("[OrderBook] %s | %d bid levels, %d ask levels | best_bid=%.2f best_ask=%.2f",
                   code, len(bid), len(ask),
                   bid[0][0] if bid else 0, ask[0][0] if ask else 0)
        return ft.RET_OK, content


class BrokerTest(ft.BrokerHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, stock_code, contents = super().on_recv_rsp(rsp_pb)
        if ret_code != ft.RET_OK:
            logger.error("BrokerTest error: %s", contents)
            return ft.RET_ERROR, contents
        bid_content, ask_content = contents[0], contents[1]
        logger.info("[Broker] code=%s | bid Brokers(%d): %s | ask Brokers(%d): %s",
                    stock_code,
                    len(bid_content) if bid_content else 0, bid_content[:3] if bid_content else "",
                    len(ask_content) if ask_content else 0, ask_content[:3] if ask_content else "")
        return ret_code


def main():
    logger.info("=== Real-time Quote Push Demo ===")

    quote_ctx = create_quote_context()

    try:
        quote_ctx.set_handler(StockQuoteTest())
        quote_ctx.set_handler(TickerTest())
        quote_ctx.set_handler(OrderBookTest())
        quote_ctx.set_handler(BrokerTest())

        subtype_list = [ft.SubType.QUOTE, ft.SubType.ORDER_BOOK, ft.SubType.TICKER, ft.SubType.BROKER]
        sub_codes = ['HK.00700', 'HK.HSImain']

        ret, _ = quote_ctx.subscribe(sub_codes, subtype_list)
        logger.info("subscribe ret=%d codes=%s subtypes=%s", ret, sub_codes, subtype_list)

        logger.info("\nReceiving pushes for 15 seconds...")
        logger.info("(Push data logs every update received from OpenD)")
        sleep(15)
        logger.info("Finished.")

    finally:
        quote_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()