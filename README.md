# Futu Python Samples

> **97 examples that actually work.** Plug in your OpenD gateway, run any script, see real market data stream back.
> No mocks, no stubs — every example talks to a live Futu OpenD instance.

[![OpenAPI Version](https://img.shields.io/badge/Futu%20OpenAPI-v5-blue)](https://openapi.futunn.com/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-green)](https://www.python.org/)
[![SDK Version](https://img.shields.io/badge/SDK-10.5.6508-blue)](https://pypi.org/project/futu-api/)
[![Changelog](https://img.shields.io/badge/changelog-v1.5.0-orange)](./CHANGELOG.md)

---

## What's New in v1.5.0

- **97 examples** covering the full Futu OpenAPI surface — grid trading, pairs trading, Monte Carlo simulation, margin monitoring, gap scanning, sector rotation, calendar spreads, earnings analysis, AH premium tracking, VWAP signals
- **10 new advanced examples (88–97)**: SL/TP engine, Monte Carlo, margin monitor, gap scanner, sector rotation, 52-week scanner, AH premium tracker, VWAP anchored trading, calendar spread builder, earnings surprise analyzer
- Full v1.0.0 through v1.4.0 changelogs below

[Full changelog →](./CHANGELOG.md)

---

## What's New in v1.0.0

- **58 examples** covering the full Futu OpenAPI surface — snapshots, K-lines, options, warrants, MACD strategy, trade lifecycle, push handlers, and advanced real-time analytics (pair trading, VWAP, order flow imbalance, options Greeks, backtesting, TWAP execution)
- **HA gateway selection** — `connect.py` probes all hosts in parallel, picks the fastest, handles RSA auto-fallback
- **Full SDK quirk documentation** — see [AGENTS.md](./AGENTS.md) for verified return types that differ from the official docs

[Full changelog →](./CHANGELOG.md)

---

## TL;DR — Up in 60 Seconds

```bash
git clone https://github.com/shing1211/futu-python-samples.git
cd futu-python-samples
pip install futu-api python-dotenv    # tested with SDK 10.5.6508
cp .env.example .env                  # ← edit with your gateway host

# pick any example — they're all self-contained
python3 examples/07_kline/main.py

That's it. No API keys, no compile step, no boilerplate to write first.
```

## What You're Getting

**Real market data, real fast.** Every example fires actual API calls against your OpenD gateway and logs the full response — every field, nothing hidden.

**Smart gateway selection.** The `connect.py` module probes all your configured OpenD hosts simultaneously, measures real TCP latency, and picks the fastest one. Both quote and trade contexts share the probe result — no redundant network calls.

**A catalog, not a tutorial.** 97 focused examples, each doing one thing well. Browse the index, find the feature you need, read the code, run it.

---

## Quick Start

**1. Install dependencies**

```bash
pip install futu-api python-dotenv
```

**2. Point it at your gateway**

```bash
cp .env.example .env
# Edit .env — set FUTU_OPEND_HOSTS to your gateway address(es)
```

**3. Run your first example**

```bash
python3 examples/00_connect_ha/main.py    # ← start here to verify connectivity
```

The `00` example probes every host, prints connection latency, and confirms the gateway is responding. If you see `Connected to ... RSA=True` in the logs, you're live.

---

## Configuration

All configuration lives in `.env` — nothing is hardcoded.

```bash
cp .env.example .env   # then edit
```

| Variable | What it does | Default |
|----------|-------------|---------|
| `FUTU_OPEND_HOSTS` | Gateway list with per-host RSA flags | uses `FUTU_ADDR` if unset |
| `FUTU_ADDR` | Single host fallback | `127.0.0.1:11111` |
| `FUTU_RSA_KEY` | Path to RSA private key | `/etc/futu/keys/private_key.pem` |
| `FUTU_TCP_TIMEOUT` | TCP probe timeout | `3` seconds |
| `FUTU_TRADE_PWD` | SIMULATE account unlock password | `123456` |

**`FUTU_OPEND_HOSTS` format:**

```bash
# localhost without RSA, two remote gateways with RSA
FUTU_OPEND_HOSTS="127.0.0.1:11111:False,172.18.208.88:11111:True"
```

The format is `host:port:is_rsa`. If you skip the `:is_rsa` part, remote hosts default to `True` (RSA on) and localhost defaults to `False` (RSA off).

> `.env` is gitignored. Never commit real gateway addresses or passwords.

---

## The Connection Module — `connect.py`

All examples (except `00`) share one connection helper:

```python
from connect import create_quote_context, create_trade_context, get_demo_trade_password

quote_ctx = create_quote_context()   # probes all hosts, picks fastest, sets up RSA
trd_ctx   = create_trade_context()   # reuses the same probe result — no extra latency

try:
    ret, df = quote_ctx.get_stock_quote("HK.00700")
    logger.info("Quote: %s", df)
finally:
    quote_ctx.close()
    trd_ctx.close()
```

What `connect.py` does for you:

- Probes all hosts in parallel with real TCP timing
- Picks the fastest reachable gateway
- Configures RSA encryption if the host requires it (with automatic fallback)
- Caches the probe result so trade and quote contexts both land on the same gateway
- Reads all config from `.env` — zero hardcoded values

---

## Examples Index

Browse by category or find the feature you need.

### Connectivity & Core

- [00](./examples/00_connect_ha/) — **HA gateway selection** — probes all hosts, picks fastest, retries RSA on failure. Start here to verify your setup.
- [01](./examples/01_snapshot/) — **Market snapshot** — fetch every stock in a market (HK, US, SH, SZ) in one call

### Market Data

- [07](./examples/07_kline/) — **Historical + current K-lines** — fetch history with pagination, get today's bar live
- [08](./examples/08_rt_ticker/) — **Tick-by-tick trades** — every trade print for a stock
- [09](./examples/09_broker_queue/) — **Broker queue depth** — who's on the bid/ask, how deep
- [10](./examples/10_orderbook/) — **10-level order book** — full bid/ask ladder with volume at each level
- [16](./examples/16_stock_quote/) — **Stock quotes** — last price, volume, turnover, bid/ask for a list of stocks
- [22](./examples/22_market_state/) — **Market state** — is the market pre-open, open, closed, or after-hours right now?
- [44](./examples/44_multi_market_snapshot/) — **Multi-market snapshot** — all four markets fetched concurrently via threading

### Filters & Screens

- [03](./examples/03_filter/) — **Stock screener** — 20+ filter criteria — price, PE, market cap, turnover, industry, flag day, and more
- [52](./examples/52_option_chain_filter/) — **Option chain filter** — slice option chains by delta, IV, moneyness, open interest using `OptionDataFilter`

### Sectors, Plates & References

- [13](./examples/13_plate/) — **Sector plates** — all plates (sectors/industries) in a market, and every stock belonging to a plate
- [17](./examples/17_owner_plate/) — **Owner plates** — which plate owns a given stock — useful for sector rotation
- [18](./examples/18_referencestock/) — **Reference stocks** — warrant and bull-bear chain reference data — the underlying and its related instruments
- [28](./examples/28_warrant/) — **Warrant data** — all warrants for an underlying — issuer, implied volatility, premium, maturity

### Capital & Fundamentals

- [19](./examples/19_capital_flow/) — **Capital flow** — where money is flowing in/out, intraday and daily heatmap
- [42](./examples/42_capital_distribution/) — **Capital distribution** — Super/Big/Mid/Small fund flow breakdown per stock — institutional tier breakdown
- [29](./examples/29_unusual/) — **Unusual activity** — unusual volume, price, technical and derivative signals — pick up early mover prints
- [27](./examples/27_code_change/) — **Code changes** — stock rename, split, and code change history
- [41](./examples/41_rehab/) — **Rehabilitation data** — ex-dividend, ex-rights, share consolidation dates — for adjusting historical prices

### Advanced Analytics & Algo Execution

- [58](./examples/58_options_greeks/) — **Options Greeks Dashboard** — Black-Scholes delta, gamma, theta, vega, rho computed live from option chain data
- [59](./examples/59_dark_pool_detector/) — **Dark Pool / Block Trade Detector** — cross-reference ticker prints vs broker queue for off-book execution signals
- [60](./examples/60_cross_market_arb/) — **Cross-Market Arbitrage Spread** — monitor HK.00700 vs US.TCEHY spread in real time
- [61](./examples/61_twap_slicer/) — **TWAP Order Slicer** — algorithmic execution: slice large orders over time using order book pricing
- [62](./examples/62_portfolio_risk/) — **Portfolio Risk Monitor** — 6 live risk metrics (concentration, leverage, margin, P&L) with threshold alerts
- [63](./examples/63_earnings_screener/) — **Earnings Volatility Screener** — pre-earnings IV/HV ratio, post-earnings unusual activity detection
- [64](./examples/64_backtesting/) — **Backtesting Framework** — SMA/RSI/MACD strategies with Sharpe ratio, drawdown, win rate
- [65](./examples/65_vol_surface/) — **Volatility Surface Builder** — moneyness × expiry IV matrix from option chains
- [66](./examples/66_multi_leg_order/) — **Multi-Leg Options Order** — vertical call spread on SIMULATE with fill monitoring
- [67](./examples/67_health_monitor/) — **Connection Health Monitor** — watchdog polling latency, subscription quota, market states

### Advanced Execution Strategies

- [68](./examples/68_trailing_stop/) — **Trailing Stop Execution** — dynamic stop-loss that follows price favorably
- [69](./examples/69_bollinger_bounce/) — **Bollinger Band Bounce** — mean-reversion via pure-Python Bollinger Bands
- [70](./examples/70_warrant_valuation/) — **Warrant Valuation Dashboard** — intrinsic/time value, implied vol ranking
- [71](./examples/71_market_regime/) — **Market Regime Detector** — ADX + rolling vol classification (trending/ranging/breakout)
- [72](./examples/72_candlestick_scanner/) — **Candlestick Pattern Scanner** — 9 classic patterns with confidence scoring
- [73](./examples/73_correlation_tracker/) — **Multi-Asset Correlation Tracker** — rolling Pearson matrix + spike detection
- [74](./examples/74_orderflow_viz/) — **Order Flow Imbalance Visualizer** — real-time ASCII imbalance chart
- [75](./examples/75_futures_term_structure/) — **Futures Term Structure & Roll Yield** — dynamic discovery, contango/backwardation
- [76](./examples/76_kelly_sizer/) — **Kelly Criterion Position Sizer** — optimal sizing with half/quarter-Kelly
- [77](./examples/77_iceberg_detector/) — **Iceberg Order Detector** — heuristic hidden order detection
- [78](./examples/78_grid_trading/) — **Grid Trading Bot** — automated buy-low/sell-high within a price range
- [79](./examples/79_pairs_trading/) — **Pairs Trading (Cointegration)** — Engle-Granger stat-arb on HK.00700 vs US.TCEHY
- [80](./examples/80_multi_leg_options/) — **Multi-Leg Options Strategy** — straddle, strangle, iron condor execution
- [81](./examples/81_portfolio_rebalance/) — **Portfolio Rebalancing Bot** — periodic target-allocation rebalancing
- [82](./examples/82_unusual_options/) — **Unusual Options Activity Scanner** — volume anomaly flagging

### Screening & Volatility

- [83](./examples/83_dividend_tracker/) — **Dividend & Corporate Action Tracker** — upcoming dividends, ex-dates, splits, rights issues
- [84](./examples/84_vwap_analysis/) — **VWAP Execution Analysis** — trade quality vs VWAP, slippage, time-bucketed breakdown
- [85](./examples/85_vol_skew/) — **Options Volatility Skew** — IV surface across strikes/expiries, Newton-Raphson solver

### Market Breadth & Alerts

- [86](./examples/86_market_breadth/) — **Market Breadth Dashboard** — Adv/Dec, McClellan, sector participation across HK/US/SH/SZ
- [87](./examples/87_watchlist_alerts/) — **Smart Watchlist Alerts** — price targets, RSI, Bollinger Band break alerts

### Risk Management (SIMULATE)

- [88](./examples/88_sl_tp_engine/) — **Stop-Loss / Take-Profit Engine** — dual SL/TP with partial exits and trailing
- [92](./examples/92_monte_carlo/) — **Monte Carlo Portfolio Simulator** — 10K path simulation with VaR and percentiles
- [96](./examples/96_margin_monitor/) — **Margin Utilization Monitor** — real-time margin tracking + liquidation price estimates

### Cross-Market & Signals

- [89](./examples/89_gap_scanner/) — **Gap Scanner** — overnight gap detection across all markets with volume confirmation
- [90](./examples/90_ah_premium/) — **AH Premium/Discount Tracker** — A-share vs H-share price comparison in real time
- [91](./examples/91_sector_rotation/) — **Sector Rotation Scanner** — RSI-based sector ranking for rotation signals
- [95](./examples/95_52week_scanner/) — **52-Week High/Low Scanner** — proximity to yearly extremes with volume confirmation
- [97](./examples/97_vwap_anchored/) — **VWAP Anchored Trading Levels** — dynamic support/resistance with volume signals

### Options Strategies (SIMULATE)

- [93](./examples/93_calendar_spread/) — **Options Calendar Spread Builder** — neutral theta plays via vol differential
- [94](./examples/94_earnings_analyzer/) — **Earnings Surprise Analyzer** — EPS surprise detection + post-earnings activity

### Real-Time Feeds (Push Handlers)

Push handlers receive streaming data from OpenD as events occur. Subscribe once, and the handler fires every time the data changes — no polling required.

- [02](./examples/02_quote_push/) — **All quote push handlers** — quote, orderbook, ticker, broker queue, all running simultaneously
- [05](./examples/05_quote_trade/) — **Quote + trade combined** — every push type in one script, with trade order/deal streams
- [14](./examples/14_cur_kline/) — **Live K-line stream** — subscribe to real-time candlestick updates
- [39](./examples/39_push_sysnotify/) — **System notifications** — login events, order fills, market alerts
- [40](./examples/40_push_trade/) — **Trade push** — live order status and deal confirmations as they happen
- [45](./examples/45_broker_handler/) — **Broker queue push** — `BrokerHandlerBase` for real-time broker depth changes. LV1 data permission required.
- [45b](./examples/45b_ticker_handler/) — **Ticker push** — `TickerHandlerBase` for every trade print with price, volume, direction
- [46](./examples/46_curkline_handler/) — **CurKline push** — `CurKlineHandlerBase` for live candle build-up before bar closes
- [47](./examples/47_price_reminder_handler/) — **Price reminder push** — `PriceReminderHandlerBase` for server-pushed price alerts
- [48](./examples/48_keepalive_handler/) — **KeepAlive push** — `KeepAliveHandlerBase` for connection heartbeat monitoring

### Trading (SIMULATE Account)

All trade examples use the **SIMULATE** account only. No real orders are placed.

- [04](./examples/04_macd_strategy/) — **MACD strategy** — calculate MACD cross signals, place simulated orders
- [06](./examples/06_stock_sell/) — **Place and modify orders** — sell with smart order types
- [11](./examples/11_accinfo/) — **Account info + positions** — cash, margin, positions, Unrealized P&L, dry-run your buying power
- [32](./examples/32_order_query/) — **Order lifecycle** — query, modify, cancel orders and their fills
- [33](./examples/33_trading_info/) — **Trading limits** — max buy/sell quantity, margin ratios
- [34](./examples/34_cancel_all/) — **Cancel all open orders** — emergency cleanup
- [35](./examples/35_cashflow/) — **Cash flow** — deposits, withdrawals, fees, corporate actions — account cash movement history
- [37](./examples/37_margin_ratio/) — **Margin ratios** — margin utilization for leveraged positions
- [38](./examples/38_order_fee/) — **Order fees** — commission, platform fee, clear fees — real cost of every order
- [49](./examples/49_acc_cash_flow/) — **Account cash flow** — `get_acc_cash_flow` on trade context (SIMULATE may be blocked by platform)
- [50](./examples/50_history_order_deal/) — **Historical orders & deals** — closed-order pipeline and historical fill records
- [51](./examples/51_acc_list/) — **Account list** — all sub-accounts (REAL + SIMULATE) with types and statuses

### Calendars & Reference Data

- [12](./examples/12_trading_days/) — **Trading days calendar** — which days each market is open
- [20](./examples/20_ipo_list/) — **IPO calendar** — upcoming and recent IPOs per market
- [21](./examples/21_future_info/) — **Futures specs** — contract size, tick size, trading hours
- [53](./examples/53_option_expiration_cycle/) — **Option expiration cycles** — full roll calendar grouped by WEEK/MONTH/QUARTER

### User Data & Alerts

- [23](./examples/23_price_reminder/) — **Price alerts** — create, query, update, delete price reminders
- [24](./examples/24_user_security/) — **Watchlist groups** — create, rename, delete watchlist groups; add and remove stocks
- [30](./examples/30_user_info/) — **User info** — account list, user profile, broker firm and account type
- [31](./examples/31_misc/) — **Misc** — flag days, rehabilitation data, watchlist group membership

### Utilities

- [15](./examples/15_sub_list/) — **Subscription list** — which stocks and what types you're subscribed to
- [25](./examples/25_option_chain/) — **Option chains** — all option contracts for an underlying grouped by expiration date
- [26](./examples/26_history_kl_quota/) — **K-line quota** — how many historical K-line API calls you've burned through today
- [36](./examples/36_stock_basicinfo/) — **Stock basic info** — name, lot size, board lot, security type
- [43](./examples/43_subscribe_lifecycle/) — **Subscribe lifecycle** — batch subscribe → query subscription → unsubscribe_all

---

## Running the Full Suite

```bash
# The proper runner — shows PASS/FAIL for all 97 examples
python3 scripts/run_all.py

# Smoke test (just checks for exceptions)
bash scripts/test_all.sh
```

How `run_all.py` classifies results:

- Push examples (`02`, `05`, `39`, `40`, `45`, `45b`, `46`, `47`, `48`, `59`) — 8s timeout, non-zero exit is expected
- `01_snapshot` — 400s timeout, fetches 21,000+ stocks across 4 markets
- `44_multi_market_snapshot` — 30s timeout, parallel multi-market fetch
- Trade examples that hit a locked password — reported as **PASS** with "trade locked" note (gateway cooldown, not a bug)
- Everything else — 30s timeout, checked for exceptions

---

## RSA and Remote Gateways

Remote OpenD instances encrypt all traffic with RSA. The SDK **does not auto-detect** remote vs localhost — you must opt in explicitly:

```python
from futu import SysConfig
SysConfig.enable_proto_encrypt(True)                    # RSA on
SysConfig.set_init_rsa_file("/path/to/private_key.pem")  # key file
ctx = OpenQuoteContext(host="remote-gateway", port=11111)
```

`connect.py` handles this for you automatically — just set `is_rsa=True` in `FUTU_OPEND_HOSTS` for remote hosts. It also retries the connection without RSA if it fails, as a fallback.

---

## SDK Reference

- **Docs** — https://openapi.futunn.com/futu-api-doc/
- **PyPI** — https://pypi.org/project/futu-api/

---

## Project Layout

```
├── .env.example            ← configuration template (copy to .env)
├── CHANGELOG.md            ← release notes
├── ARCHITECTURE.md         ← system design, schematics
├── CONTRIBUTING.md         ← how to add examples
├── TROUBLESHOOTING.md      ← common problems and fixes
├── examples/
│   ├── connect.py          ← HA gateway helper (shared by all examples)
│   ├── README.md           ← full 97-example index
│   ├── 00_connect_ha/      ← standalone HA algorithm
│   ├── 01_snapshot/        ← market snapshot
│   │
│   ├── ... (02–87)
│   │
│   ├── 88_trailing_stop/   ← dynamic trailing stop-loss
│   ├── 89_gap_scanner/     ← overnight gap detection
│   ├── 90_ah_premium/      ← A-share vs H-share premium tracking
│   ├── 91_sector_rotation/ ← RSI-based sector ranking
│   ├── 92_monte_carlo/     ← portfolio Monte Carlo simulation
│   ├── 93_calendar_spread/ ← options calendar spread builder
│   ├── 94_earnings_analyzer/ ← earnings surprise analysis
│   ├── 95_52week_scanner/  ← 52-week extreme proximity scanner
│   ├── 96_margin_monitor/  ← real-time margin utilization monitor
│   └── 97_vwap_anchored/   ← VWAP-based support/resistance signals
├── scripts/
│   └── run_all.py          ← automated test runner
```

## See Also

| Document | What it covers |
|----------|---------------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System design, sequence diagrams, execution flows, directory structure |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Adding examples, code conventions, return type reference, testing |
| [PLANS.md](./PLANS.md) | Detailed implementation plans for advanced examples |
| [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) | Gateway issues, RSA errors, trade lockout, subscription quota, pandas pitfalls |
| [CHANGELOG.md](./CHANGELOG.md) | Version history and release notes |
| [AGENTS.md](./AGENTS.md) | SDK quirks reference for AI coding tools |

---

## License

MIT — see [LICENSE](./LICENSE).