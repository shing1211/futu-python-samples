# Examples

42 examples covering the full Futu OpenAPI surface — quote, trade, and push handlers.

All use `examples/connect.py` for HA gateway selection and RSA configuration.

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
| 15 | [15_sub_list](./15_sub_list/) | Query subscription list (query_subscription) |
| 16 | [16_stock_quote](./16_stock_quote/) | Real-time quote fields (get_stock_quote) |
| 17 | [17_owner_plate](./17_owner_plate/) | Owner plate + referencestock list |
| 18 | [18_referencestock](./18_referencestock/) | Warrant/bull-bear reference stocks |
| 19 | [19_capital_flow](./19_capital_flow/) | Capital flow + capital distribution |
| 20 | [20_ipo_list](./20_ipo_list/) | IPO calendar per market |
| 21 | [21_future_info](./21_future_info/) | Futures contract details |
| 22 | [22_market_state](./22_market_state/) | Market state (pre/open/after/closed) |
| 23 | [23_price_reminder](./23_price_reminder/) | Price alert setup and query |
| 24 | [24_user_security](./24_user_security/) | Watchlist group management |
| 25 | [25_option_chain](./25_option_chain/) | Option chain + expiration dates |
| 26 | [26_history_kl_quota](./26_history_kl_quota/) | Historical K-line quota and usage |
| 27 | [27_code_change](./27_code_change/) | Stock code change records |
| 28 | [28_warrant](./28_warrant/) | Warrant data by underlying |
| 29 | [29_unusual](./29_unusual/) | Technical/financial/derivative unusual alerts |
| 30 | [30_user_info](./30_user_info/) | Account list, user info, broker firm |
| 31 | [31_misc](./31_misc/) | Holding changes, rehab data, user security groups |
| 32 | [32_order_query](./32_order_query/) | Order query, modify, cancel, deal history |
| 33 | [33_trading_info](./33_trading_info/) | Max buy/sell quantity (acctradinginfo_query) |
| 34 | [34_cancel_all](./34_cancel_all/) | Cancel all open orders |
| 35 | [35_cashflow](./35_cashflow/) | Account cash flow history |
| 36 | [36_stock_basicinfo](./36_stock_basicinfo/) | Stock basic info by market or code list |
| 37 | [37_margin_ratio](./37_margin_ratio/) | Margin ratio for positions |
| 38 | [38_order_fee](./38_order_fee/) | Order fee query |
| 39 | [39_push_sysnotify](./39_push_sysnotify/) | System notification push (SysNotifyHandlerBase) |
| 40 | [40_push_trade](./40_push_trade/) | Trade order/deal push (TradeOrder/DealHandlerBase) |
| 41 | [41_rehab](./41_rehab/) | Rehabilitation/ex-dividend/ex-right data |
