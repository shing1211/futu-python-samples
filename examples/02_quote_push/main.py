# -*- coding: utf-8 -*-
"""
Examples for use the python functions: get push data
"""
from time import sleep
from futu import *
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from connect import create_quote_context


class StockQuoteTest(StockQuoteHandlerBase):
    """
    获得报价推送数据
    """
    def on_recv_rsp(self, rsp_pb):
        """数据响应回调函数"""
        ret_code, content = super(StockQuoteTest, self).on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            logger.debug("StockQuoteTest: error, msg: %s" % content)
            return RET_ERROR, content
        print("* StockQuoteTest : %s" % content)
        return RET_OK, content


class TickerTest(TickerHandlerBase):
    """ 获取逐笔推送数据 """
    def on_recv_rsp(self, rsp_pb):
        """数据响应回调函数"""
        ret_code, content = super(TickerTest, self).on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            print("* TickerTest: error, msg: %s" % content)
            return RET_ERROR, content
        return RET_OK, content


class OrderBookTest(OrderBookHandlerBase):
    """ 获得摆盘推送数据 """
    def on_recv_rsp(self, rsp_pb):
        """数据响应回调函数"""
        ret_code, content = super(OrderBookTest, self).on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            print("* OrderBookTest: error, msg: %s" % content)
            return RET_ERROR, content
        return RET_OK, content


class BrokerTest(BrokerHandlerBase):
    """ 获取经纪队列推送数据 """
    def on_recv_rsp(self, rsp_pb):
        """数据响应回调函数"""
        ret_code, stock_code, contents = super(BrokerTest, self).on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            print("* BrokerTest: error, msg: %s" % contents)
            return RET_ERROR, contents
        return ret_code


def quote_test():
    '''
    行情接口调用测试
    :return:
    '''
    quote_ctx = create_quote_context()

    # 设置异步回调接口
    quote_ctx.set_handler(StockQuoteTest())
    quote_ctx.set_handler(TickerTest())
    quote_ctx.set_handler(OrderBookTest())
    quote_ctx.set_handler(BrokerTest())
    quote_ctx.start()

    # 获取推送数据
    subtype_list = [SubType.QUOTE, SubType.ORDER_BOOK, SubType.TICKER, SubType.BROKER]
    sub_codes = ['HK.00700', 'HK.999010']
    print("* subscribe : {}\n".format(quote_ctx.subscribe(sub_codes, subtype_list)))


if __name__ =="__main__":
    set_futu_debug_model(True)
    ''' 行情api测试 '''
    quote_test()
