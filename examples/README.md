# Examples

## Index

| # | Name | Description |
|---|------|-------------|
| 00 | [00_connect_ha](./00_connect_ha/) | HA gateway connection — TCP probe, per-host RSA, auto-fallback |
| 01 | [01_snapshot](./01_snapshot/) | Market snapshot for all stocks in a market |
| 02 | [02_quote_push](./02_quote_push/) | Real-time quote/orderbook/ticker/broker push via handlers |
| 03 | [03_filter](./03_filter/) | Stock screener with SimpleFilter + FinancialFilter |
| 04 | [04_macd_strategy](./04_macd_strategy/) | MACD trading signal strategy (buy/sell on cross) |
| 05 | [05_quote_trade](./05_quote_trade/) | Full quote + trade push with all handler types |
| 06 | [06_stock_sell](./06_stock_sell/) | Simple and smart sell functions |
| 07 | [07_kline](./07_kline/) | K-line data — get_cur_kline + request_history_kline |
| 08 | [08_rt_ticker](./08_rt_ticker/) | Real-time tick data — get_rt_ticker + get_rt_data |
| 09 | [09_broker_queue](./09_broker_queue/) | Broker queue — bid/ask queue data |
| 10 | [10_orderbook](./10_orderbook/) | Order book — 10-level bid/ask depth |
| 11 | [11_accinfo](./11_accinfo/) | Account info + positions (accinfo_query / position_list_query) |
| 12 | [12_trading_days](./12_trading_days/) | Trading days calendar per market |
| 13 | [13_plate](./13_plate/) | Plate (sector/industry) listing and stock membership |
| 14 | [14_cur_kline](./14_cur_kline/) | Real-time K-line push via CurKlineHandlerBase |

## 07 — kline

Get current and historical candlestick (K-line) data.

```python
from connect import create_quote_context

ctx = create_quote_context()
ret, data = ctx.get_cur_kline("HK.00700", num=10, ktype=KLType.K_DAY, AuType=AuType.qfq)
ret, data = ctx.request_history_kline("HK.00700", start="2026-01-01", end="2026-05-12",
                                       ktype=KLType.K_DAY, AuType=AuType.qfq)
ctx.close()
```

## 08 — rt_ticker

Real-time transaction (tick) data and minute-level time-series data.

```python
ret, data = ctx.get_rt_ticker("HK.00700", num=50)
ret, data = ctx.get_rt_data("HK.00700")
```

## 09 — broker_queue

Broker bid/ask queue — shows top brokers on each side of the book.

```python
ctx.subscribe(code, SubType.BROKER)
ret, bid_data, ask_data = ctx.get_broker_queue(code)
```

## 10 — orderbook

Level-10 order book (bid/ask depth with volume per price level).

```python
ctx.subscribe(code, SubType.ORDER_BOOK)
ret, data = ctx.get_order_book(code, num=10)
```

## 11 — accinfo

Account capital and position queries.

```python
trd_ctx = create_trade_context(filter_trdmarket=TrdMarket.HK)
trd_ctx.unlock_trade("123456")
ret, data = trd_ctx.accinfo_query()
ret, data = trd_ctx.position_list_query()
```

## 12 — trading_days

Query trading days for a given market and date range.

```python
ret, data = ctx.request_trading_days(Market.HK, "2026-01-01", "2026-12-31")
```

## 13 — plate

List industry/sector plates and get constituent stocks.

```python
ret, data = ctx.get_plate_list(Market.HK, Plate.ALL)
ret, data = ctx.get_plate_stock("HK.BK1001")
```

## 14 — cur_kline

Real-time K-line push using `CurKlineHandlerBase`.

```python
class MyKlineHandler(CurKlineHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, kline_list = super().on_recv_rsp(rsp_pb)
        # kline_list[0].code, .time_key, .open, .high, .low, .close, .volume
        return ret_code, kline_list

ctx.set_handler(MyKlineHandler())
ctx.subscribe("HK.00700", SubType.K_DAY)
```
