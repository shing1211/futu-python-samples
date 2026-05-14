# Examples

68 examples covering the full Futu OpenAPI surface — every API call documented, every response demonstrated, zero mocks.

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
| [47](./47_price_reminder_handler/) | Price Reminder Push | `PriceReminderHandlerBase` — server-pushed alerts when your price targets are hit |
| [48](./48_keepalive_handler/) | KeepAlive Push | `KeepAliveHandlerBase` — heartbeat monitoring between client and OpenD |
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

### Filtering & Screening

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

### Fundamentals & Flow

| # | Name | What you'll see |
|---|------|----------------|
| [19](./19_capital_flow/) | Capital Flow | Intraday and daily capital flow heatmap — where money is going in/out |
| [42](./42_capital_distribution/) | Capital Distribution | Super/Big/Mid/Small fund flow breakdown per stock — institutional tier breakdown |
| [29](./29_unusual/) | Unusual Activity | Unusual volume, price, technical and derivative signals — pick up early mover prints |
| [27](./27_code_change/) | Code Changes | Stock rename, split, and code change history |
| [41](./41_rehab/) | Rehabilitation Data | Ex-dividend, ex-rights, share consolidation dates — for adjusting historical prices |

### Trading — SIMULATE Account

> All trade examples are for the **SIMULATE account only**. No real orders are placed.

| # | Name | What you'll see |
|---|------|----------------|
| [04](./04_macd_strategy/) | MACD Strategy | Calculate MACD cross signals from historical K-lines, place simulated buy/sell orders |
| [06](./06_stock_sell/) | Stock Sell | Place simple and smart-order sell orders, modify quantity and price mid-flight |
| [11](./11_accinfo/) | Account Info | Cash, margin, positions, Unrealized P&L, dry-run your buying power |
| [32](./32_order_query/) | Order Query | Full order lifecycle — query open orders, fills, modify price/qty, cancel |
| [33](./33_trading_info/) | Trading Info | Max buy/sell quantity, margin ratio, required margin per lot |
| [34](./34_cancel_all/) | Cancel All Orders | Panic button — cancel every open order at once |
| [35](./35_cashflow/) | Cash Flow | Deposits, withdrawals, fees, corporate actions — account cash movement history |
| [37](./37_margin_ratio/) | Margin Ratio | Margin utilization for leveraged positions |
| [38](./38_order_fee/) | Order Fees | Commission, platform fee, clear fees — real cost of every order |
| [49](./49_acc_cash_flow/) | Account Cash Flow | Cash movement history via trade context API — deposits, withdrawals, fees |
| [50](./50_history_order_deal/) | Historical Orders & Deals | Full closed-order pipeline and historical fill records |
| [51](./51_acc_list/) | Account List | All sub-accounts under your user — REAL and SIMULATE, with types and statuses |

### Calendars & Reference

| # | Name | What you'll see |
|---|------|----------------|
| [12](./12_trading_days/) | Trading Days | Which days each market is open — useful for backtesting scheduling |
| [20](./20_ipo_list/) | IPO Calendar | Upcoming and recent IPOs per market — issue price, listing date, status |
| [21](./21_future_info/) | Futures Info | Contract spec sheet — tick size, contract multiplier, trading hours |
| [53](./53_option_expiration_cycle/) | Option Expiration Cycles | Full roll calendar grouped by WEEK/MONTH/QUARTER cycle |

### User Data & Alerts

| # | Name | What you'll see |
|---|------|----------------|
| [23](./23_price_reminder/) | Price Alerts | Create price reminders, list active alerts, update trigger prices, delete alerts |
| [24](./24_user_security/) | Watchlists | Create, rename, delete watchlist groups; add and remove stocks |
| [30](./30_user_info/) | User Info | Account list, user profile, broker firm and account type |
| [31](./31_misc/) | Misc | Flag days, rehabilitation data, watchlist group membership |

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

### Utilities

| # | Name | What you'll see |
|---|------|----------------|
| [15](./15_sub_list/) | Subscription List | What you're subscribed to and at which push frequency |
| [25](./25_option_chain/) | Option Chains | All option contracts for an underlying grouped by expiration date |
| [26](./26_history_kl_quota/) | K-Line Quota | How many historical K-line API calls you've burned through today |
| [36](./36_stock_basicinfo/) | Stock Basic Info | Name, lot size, board lot, security type for a whole market or a specific list |
| [43](./43_subscribe_lifecycle/) | Subscribe Lifecycle | Full cycle: batch subscribe → query subscription → unsubscribe; manage subscription quota |