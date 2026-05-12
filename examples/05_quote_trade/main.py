# -*- coding: utf-8 -*-
"""完整行情+交易推送示例

Demonstrates all push handlers on a single quote context + trade context:
  - StockQuoteHandlerBase: real-time quote
  - CurKlineHandlerBase: live K-line bar updates
  - RTDataHandlerBase: intraday minute-level data
  - TickerHandlerBase: tick-by-tick trades
  - OrderBookHandlerBase: order book depth
  - BrokerHandlerBase: broker queue
  - SysNotifyHandlerBase: system notifications
  - TradeOrderHandlerBase: order status changes (on trade context)
  - TradeDealHandlerBase: trade executions (on trade context)

This is a comprehensive showcase of all available push types.
Run with SIMULATE account and place test orders to see trade pushes.
"""
import logging
from time import sleep
from futu import *
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from connect import create_quote_context, create_trade_context, get_demo_trade_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


class StockQuoteTest(StockQuoteHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, content = super().on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            return RET_ERROR, content
        logger.info("[Quote] %s", content)
        return RET_OK, content


class CurKlineTest(CurKlineHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, content = super().on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            logger.warning("CurKline error: %s", content)
            return RET_OK, content
        for k in content:
            logger.info("[Kline] code=%s time=%s O=%.2f H=%.2f L=%.2f C=%.2f vol=%d",
                        k.code, k.time_key, k.open, k.high, k.low, k.close, k.volume)
        return RET_OK, content


class RTDataTest(RTDataHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, content = super().on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            logger.error("RTData error: %s", content)
            return RET_ERROR, content
        logger.info("[RTData] %s", content)
        return RET_OK, content


class TickerTest(TickerHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, content = super().on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            logger.error("Ticker error: %s", content)
            return RET_ERROR, content
        logger.info("[Ticker] %s", content)
        return RET_OK, content


class OrderBookTest(OrderBookHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, content = super().on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            logger.error("OrderBook error: %s", content)
            return RET_ERROR, content
        logger.info("[OrderBook] code=%s Bid[0]=%.2f Ask[0]=%.2f", content.get("code"), content.get("Bid", [[0]])[0][0], content.get("Ask", [[0]])[0][0])
        return RET_OK, content


class BrokerTest(BrokerHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, stock_code, contents = super().on_recv_rsp(rsp_pb)
        if ret_code == RET_OK:
            logger.info("[Broker] code=%s bid_count=%d ask_count=%d", stock_code,
                        len(contents[0]) if contents[0] else 0, len(contents[1]) if contents[1] else 0)
        return ret_code


class SysNotifyTest(SysNotifyHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, content = super().on_recv_rsp(rsp_pb)
        if ret_code == RET_OK:
            main_type, sub_type, msg = content
            logger.info("[SysNotify] type=%s subtype=%s msg=%s", main_type, sub_type, msg)
        else:
            logger.error("[SysNotify] error: %s", content)
        return ret_code, content


class TradeOrderTest(TradeOrderHandlerBase):
    def on_recv(self, rsp_str):
        ret, content = super().on_recv(rsp_str)
        if ret == RET_OK:
            logger.info("[TradeOrder] %s", content)
        return ret, content


class TradeDealTest(TradeDealHandlerBase):
    def on_recv(self, rsp_str):
        ret, content = super().on_recv(rsp_str)
        if ret == RET_OK:
            logger.info("[TradeDeal] %s", content)
        return ret, content


def main():
    logger.info("=== Full Quote+Trade Push Demo ===")

    quote_ctx = create_quote_context()
    trd_ctx = create_trade_context(filter_trdmarket=TrdMarket.HK)

    try:
        # Quote push handlers
        quote_ctx.set_handler(StockQuoteTest())
        quote_ctx.set_handler(CurKlineTest())
        quote_ctx.set_handler(RTDataTest())
        quote_ctx.set_handler(TickerTest())
        quote_ctx.set_handler(OrderBookTest())
        quote_ctx.set_handler(BrokerTest())
        quote_ctx.set_handler(SysNotifyTest())

        # Trade push handlers
        trd_ctx.set_handler(TradeOrderTest())
        trd_ctx.set_handler(TradeDealTest())

        pwd = get_demo_trade_password()
        ret, data = trd_ctx.unlock_trade(pwd)
        logger.info("unlock_trade: ret=%d data=%s", ret, data)

        # Subscribe: HK.00700 for most types; HK.HSImain for index
        subtype_list = [
            SubType.QUOTE,
            SubType.ORDER_BOOK,
            SubType.TICKER,
            SubType.K_DAY,
            SubType.K_30M,
            SubType.RT_DATA,
            SubType.BROKER,
        ]
        sub_codes = ['HK.00700', 'HK.HSImain']
        ret = quote_ctx.subscribe(sub_codes, subtype_list)
        logger.info("subscribe ret=%d", ret)

        logger.info("\nListening for pushes (30s)... Place SIMULATE orders to see trade pushes.")
        sleep(30)
        logger.info("Finished.")

    finally:
        quote_ctx.close()
        trd_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    set_futu_debug_model(True)
    main()