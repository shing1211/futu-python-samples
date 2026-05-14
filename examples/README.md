# Examples

87 examples covering the full Futu OpenAPI surface — every API call documented, every response demonstrated, zero mocks.

All scripts import `examples/connect.py` for HA gateway selection and RSA configuration.

---

## Index

### Get Going First

| # | Name | What you'll see |
|---|------|----------------|
| [00](./00_connect_ha/) | HA Gateway | TCP probe all your hosts, pick the fastest, handle RSA. Start here to confirm your setup is solid. |

### Live Market Feeds

| # | Name | What you'll see |
|---|------|----------------|
| [02](./02_quote_push/) | Quote Push | All four quote handlers running together — stock quotes, order book updates, tick-by-tick prints, broker queue changes |
| [05](./05_quote_trade/) | Quote + Trade Push | Every push type in one script: K-lines, trades, orderbook, and live trade order/deal events |
| [14](./14_cur_kline/) | Live K-Line Stream | Subscribe to real-time candlestick updates as they print |
| [39](./39_push_sysnotify/) | System Notifications | Login events, order fills, market state changes — push directly from OpenD |
| [40](./40_push_trade/) | Trade Push | Watch orders go from submitted → filled → partially filled in real time |
| [45](./45_broker_handler/) | Broker Queue Push | `BrokerHandlerBase` — real-time push when broker queue changes. LV1 data permission required. |
| [45b](./45b_ticker_handler/) | Ticker Push | `TickerHandlerBase` — every trade print with price, volume, direction, and millisecond timestamp |
| [46](./46_curkline_handler/) | CurKline Push | `CurKlineHandlerBase` — live candle build-up as it forms, before the bar closes |
| [47](./47_price_reminder_handler/) | Price Reminder Push | `PriceReminderHandlerBase` for server-pushed price alerts |
| [48](./48_keepalive_handler/) | KeepAlive Push | `KeepAliveHandlerBase` for connection heartbeat monitoring |
| [54](./54_pair_trading/) | Pair Trading Signal | Rolling z-score spread between HK.00700 and HK.09988 via CurKlineHandler — statistical arbitrage signal in real time |
| [56](./56_order_flow_imbalance/) | Order Flow Imbalance | ORDER_BOOK push accumulation — measures directional pressure as net bid vs ask volume delta over time |
| [57](./57_vwap_benchmark/) | VWAP Benchmark | TICKER push stream → running VWAP, deviation in bps, simulated entry P&L — execution quality in real time |

### Static & Historical Market Data

| # | Name | What you'll see |
|---|------|----------------|
| [01](./01_snapshot/) | Market Snapshot | Every single stock in a market — price, volume, turnover, bid/ask — in one shot |
| [44](./44_multi_market_snapshot/) | Multi-Market Snapshot | All four markets (HK/US/SH/SZ) fetched concurrently via threading |
| [55](./55_momentum_screener/) | Momentum Screener | RSI + MACD across Daily/60M/15M for 8 HK stocks — multi-timeframe signal confluence |
| [07](./07_kline/) | K-Line History | Historical K-lines with pagination + today's live bar via `get_cur_kline` |
| [08](./08_rt_ticker/) | Tick Data | Every trade print — exact time, price, volume, direction — for a stock |
| [09](./09_broker_queue/) | Broker Queue | Who sits on the bid and ask, how many lots each broker is showing |
| [10](./10_orderbook/) | Order Book | Full 10-level bid/ask ladder — price, volume, order count at each level |
| [16](./16_stock_quote/) | Stock Quote | Last price, open, high, low, volume, turnover for a list of stocks |
| [22](./22_market_state/) | Market State | Is the market pre-open, open, closed, or after-hours right now? |

### Filters & Screening

| # | Name | What you'll see |
|---|------|----------------|
| [03](./03_filter/) | Stock Screener | 20+ filter criteria — price, PE, market cap, turnover, industry, flag day, and more |
| [52](./52_option_chain_filter/) | Option Chain Filter | Slice option chains by delta, IV, moneyness, OI using `OptionDataFilter` |

### Sectors, Plates & References

| # | Name | What you'll see |
|---|------|----------------|
| [13](./13_plate/) | Sector Plates | All plates (sectors/industries) in a market, and every stock belonging to a plate |
| [17](./17_owner_plate/) | Owner Plates | Which plate owns a given stock — useful for sector rotation |
| [18](./18_referencestock/) | Reference Stocks | Warrant and bull-bear chain reference data — the underlying and its related instruments |
| [28](./28_warrant/) | Warrant Data | All warrants for an underlying — issuer, implied volatility, premium, maturity |

### Capital & Fundamentals

| # | Name | What you'll see |
|---|------|----------------|
| [19](./19_capital_flow/) | Capital Flow | Intraday and daily capital flow heatmap — where money is flowing in/out |
| [42](./42_capital_distribution/) | Capital Distribution | Super/Big/Mid/Small fund flow breakdown per stock — institutional tier breakdown |
| [29](./29_unusual/) | Unusual Activity | Unusual volume, price, technical and derivative signals — pick up early mover prints |
| [27](./27_code_change/) | Code Changes | Stock rename, split, and code change history |
| [41](./41_rehab/) | Rehabilitation Data | Ex-dividend, ex-rights, share consolidation dates — for adjusting historical prices |

### Advanced Analytics & Algo Execution

| # | Name | What you'll see |
|---|------|----------------|
| [58](./58_options_greeks/) | Options Greeks | Live delta/gamma/theta/vega/rho from option chain data — pure Python Black-Scholes |
| [59](./59_dark_pool_detector/) | Dark Pool Detector | Cross-reference TICKER + BROKER push to flag off-book trades |
| [60](./60_cross_market_arb/) | Cross-Market Arb | HK.00700 vs US.TCEHY spread tracking — live dual-market quote monitoring |
| [61](./61_twap_slicer/) | TWAP Slicer | Slice large orders over time using ORDER_BOOK pricing (SIMULATE) |
| [62](./62_portfolio_risk/) | Portfolio Risk | 6 live risk metrics — concentration, leverage, margin, P&L alerts |
| [63](./63_earnings_screener/) | Earnings Screener | Pre-earnings IV/HV ratio + post-earnings unusual activity |
| [64](./64_backtesting/) | Backtesting | SMA/RSI/MACD strategies with Sharpe, drawdown, win rate |
| [65](./65_vol_surface/) | Vol Surface | Moneyness × expiry IV matrix from option chains |
| [66](./66_multi_leg_order/) | Multi-Leg Options | Vertical call spread on SIMULATE — 2-leg fill monitoring |
| [67](./67_health_monitor/) | Health Monitor | Watchdog — latency, subscription quota, market state polling |

### Advanced Execution Strategies

| # | Name | What you'll see |
|---|------|----------------|
| [68](./68_trailing_stop/) | Trailing Stop Execution | Dynamic stop-loss that follows price favorably with order replacement |
| [69](./69_bollinger_bounce/) | Bollinger Band Bounce | Mean-reversion via pure-Python Bollinger Bands (statistics.pstdev) |
| [70](./70_warrant_valuation/) | Warrant Valuation Dashboard | Intrinsic/time value, simplified implied vol, mispricing ranking |
| [71](./71_market_regime/) | Market Regime Detector | ADX + rolling vol — classifies TRENDING / RANGING / BREAKOUT |
| [72](./72_candlestick_scanner/) | Candlestick Pattern Scanner | 9 classic patterns with confidence scoring + trend confirmation |
| [73](./73_correlation_tracker/) | Multi-Asset Correlation Tracker | Rolling Pearson matrix + spike detection across 10+ tickers |
| [74](./74_orderflow_viz/) | Order Flow Imbalance Visualizer | Real-time ASCII imbalance bar chart using ORDER_BOOK push |
| [75](./75_futures_term_structure/) | Futures Term Structure & Roll Yield | Dynamic futures discovery, contango/backwardation, ASCII chart |
| [76](./76_kelly_sizer/) | Kelly Criterion Position Sizer | Optimal sizing with half/quarter-Kelly, ATR-based stop |
| [77](./77_iceberg_detector/) | Iceberg Order Detector | Heuristic hidden order detection via order book dynamics |
| [78](./78_grid_trading/) | Grid Trading Bot | Automated buy-low/sell-high within a defined price range |
| [79](./79_pairs_trading/) | Pairs Trading (Cointegration) | Engle-Granger stat-arb — HK.00700 vs US.TCEHY |
| [80](./80_multi_leg_options/) | Multi-Leg Options Strategy | Straddle, strangle, iron condor execution on SIMULATE |
| [81](./81_portfolio_rebalance/) | Portfolio Rebalancing Bot | Periodic target-allocation rebalancing with live positions |
| [82](./82_unusual_options/) | Unusual Options Activity Scanner | Volume anomaly flagging across full option chain |

### Screening & Volatility

| # | Name | What you'll see |
|---|------|----------------|
| [83](./83_dividend_tracker/) | Dividend & Corporate Action Tracker | Upcoming dividends, ex-dates, splits, rights issues for watchlist |
| [84](./84_vwap_analysis/) | VWAP Execution Analysis | Trade quality vs VWAP benchmark, slippage analysis, time-bucketed breakdown |
| [85](./85_vol_skew/) | Options Volatility Skew | Implied vol surface across strikes/expiries with Newton-Raphson IV solver |

### Market Breadth & Alerts

| # | Name | What you'll see |
|---|------|----------------|
| [86](./86_market_breadth/) | Market Breadth Dashboard | Adv/Dec, McClellan Oscillator, sector participation across HK/US/SH/SZ |
| [87](./87_watchlist_alerts/) | Smart Watchlist Alerts | Price targets, RSI, Bollinger Band break alerts with cooldown logic |

### Real-Time Feeds (Push Handlers)

Push handlers receive streaming data from OpenD as events occur. Subscribe once, and the handler fires every time the data changes — no polling required.

| # | Name | What you'll see |
|---|------|----------------|
| [02](./02_quote_push/) | All quote push handlers | Quote, orderbook, ticker, broker queue — all running simultaneously |
| [05](./05_quote_trade/) | Quote + trade combined | Every push type in one script, with trade order/deal streams |
| [14](./14_cur_kline/) | Live K-Line Stream | Subscribe to real-time candlestick updates as they print |
| [39](./39_push_sysnotify/) | System Notifications | Login events, order fills, market alerts |
| [40](./40_push_trade/) | Trade Push | Live order status and deal confirmations as they happen |
| [45](./45_broker_handler/) | Broker Queue Push | `BrokerHandlerBase` for real-time broker depth changes (LV1 req.) |
| [45b](./45b_ticker_handler/) | Ticker Push | `TickerHandlerBase` for every trade print with price, volume, direction |
| [46](./46_curkline_handler/) | CurKline Push | `CurKlineHandlerBase` for live candle build-up before bar closes |
| [47](./47_price_reminder_handler/) | Price Reminder Push | `PriceReminderHandlerBase` for server-pushed price alerts |
| [48](./48_keepalive_handler/) | KeepAlive Push | `KeepAliveHandlerBase` for connection heartbeat monitoring |

### Trading (SIMULATE Account)

All trade examples use the **SIMULATE** account only. No real orders are placed.

| # | Name | What you'll see |
|---|------|----------------|
| [04](./04_macd_strategy/) | MACD strategy | Calculate MACD cross signals, place simulated orders |
| [06](./06_stock_sell/) | Place and modify orders | Sell with smart order types |
| [11](./11_accinfo/) | Account info + positions | Cash, margin, positions, P&L |
| [32](./32_order_query/) | Order lifecycle | Query, modify, cancel orders and their fills |
| [33](./33_trading_info/) | Trading limits | Max buy/sell quantity, margin ratios |
| [34](./34_cancel_all/) | Cancel all open orders | Emergency cleanup |
| [35](./35_cashflow/) | Cash flow history | Deposits, withdrawals, fees |
| [37](./37_margin_ratio/) | Margin ratios | Margin utilization for leveraged positions |
| [38](./38_order_fee/) | Order fees | Commission, platform fee, clear fees per order |
| [49](./49_acc_cash_flow/) | Account cash flow | `get_acc_cash_flow` on trade context |
| [50](./50_history_order_deal/) | Historical orders & deals | Closed-order pipeline and historical fills |
| [51](./51_acc_list/) | Account list | All sub-accounts (REAL + SIMULATE) with types and statuses |

### Calendars & Reference Data

| # | Name | What you'll see |
|---|------|----------------|
| [12](./12_trading_days/) | Trading days calendar | Which days each market is open |
| [20](./20_ipo_list/) | IPO calendar | Upcoming and recent IPOs per market |
| [21](./21_future_info/) | Futures specs | Contract size, tick size, trading hours |
| [53](./53_option_expiration_cycle/) | Option expiration cycles | Full roll calendar grouped by WEEK/MONTH/QUARTER |

### User Data & Administration

| # | Name | What you'll see |
|---|------|----------------|
| [23](./23_price_reminder/) | Price alerts | Create, query, update, delete price reminders |
| [24](./24_user_security/) | Watchlist groups | Create, rename, delete watchlist groups; add and remove stocks |
| [30](./30_user_info/) | User info | Account list, user profile, broker firm and account type |
| [31](./31_misc/) | Misc | Flag days, rehabilitation data, watchlist group membership |

### Quota & Utility

| # | Name | What you'll see |
|---|------|----------------|
| [15](./15_sub_list/) | Subscription list | Which stocks and what types you're subscribed to |
| [25](./25_option_chain/) | Option chains | All option contracts for an underlying grouped by expiration date |
| [26](./26_history_kl_quota/) | K-line quota | How many historical K-line API calls you've burned through today |
| [36](./36_stock_basicinfo/) | Stock basic info | Name, lot size, board lot, security type for a market or code list |
| [43](./43_subscribe_lifecycle/) | Subscribe lifecycle | Batch subscribe → query subscription → unsubscribe_all |
| [58](./58_options_greeks/) | Options Greeks Dashboard | Black-Scholes delta, gamma, theta, vega, rho computed live |
| [65](./65_vol_surface/) | Volatility Surface Builder | Moneyness × expiry IV matrix from option chains |