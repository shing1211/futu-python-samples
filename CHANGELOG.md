# Changelog

All notable changes to this project are documented here.

---

## [2.0.0] — 2026-06-29

### Added

- **SDK 10.8.6808 upgrade** — upgraded from 10.7.6708 to 10.8.6808. 35+ new SDK APIs, 0 removed:
  - Market & news search: `get_search_quote`, `get_search_news`
  - Technical indicator catalog: `get_indicator_list`
  - Options data: Put/Call ratio via `get_option_market_statistic`, 0DTE screener, earnings options, seller strategy, option unusual activity, option contract ranking, historical volatility
  - Macro & Fed: `get_macro_indicator_list`, `get_macro_indicator_history`, `get_fed_watch_target_rate`, `get_fed_watch_dot_plot`, `get_economic_calendar`
  - Institutional tracking: `get_institution_list`, `get_institution_profile`, `get_institution_holding_list`, `get_institution_holding_change`, `get_institution_distribution`
  - Industry chain: `get_industrial_chain_list`, `get_industrial_chain_detail`, `get_industrial_chain_by_plate`, `get_industrial_plate_info`, `get_industrial_plate_stock`
  - Trending: `get_hot_list`
- **7 new examples (118–124)** demonstrating SDK 10.8.6808 APIs:
  - 118 (`market_search`): Keyword-based market instrument + news/announcement search
  - 119 (`option_0dte`): 0DTE (zero-days-to-expiry) options underlying & contract screener
  - 120 (`option_earnings`): Earnings options screener with IV crush, option flow & unusual activity
  - 121 (`option_seller`): Option seller strategy screen with premium, annualized return & OTM probability
  - 122 (`fedwatch_macro`): Fed rate monitor, macro indicator trends & economic calendar
  - 123 (`institutional_13f`): 13F-style institutional holder tracking with position changes & portfolio allocation
  - 124 (`industry_chain`): Industry chain explorer with upstream/downstream chain map & sector stock listing

### Changed

- `requirements.txt`: `futu-api>=10.7.6708` → `>=10.8.6808`
- `pyproject.toml`: `dependencies` now requires `futu-api>=10.8.6808`
- All doc version strings updated to `10.8.6808`
- `README.md`: badge → SDK 10.8.6808, changelog → v2.0.0, count → 124 examples
- `examples/README.md`: count → 124, 7 new entries across `Filters & Screening`, `Options Strategies`, `Capital & Fundamentals`, `Sectors, Plates & References`
- `scripts/run_all.py`: 7 new SLOW_EXAMPLES entries (30s each)

### Fixed

- Zero breaking changes detected — all 117 existing examples compatible with SDK 10.8.6808 without modification
- `connect.py` `RetCode` shim remains in place (SDK 10.8 still does not have `ft.RetCode`)

## [1.9.0] — 2026-06-05

### Added

- **SDK 10.7.6708 upgrade** — upgraded from 10.6.6608 to 10.7.6708. 6 new SDK APIs added, 0 removed:
  - `get_option_strategy` / `get_option_strategy_analysis` / `get_option_strategy_spread`
  - `place_combo_order` / `comboorder_tradinginfo_query`
  - `get_order_book(…, order_book_type=OrderBookType.ODD)`
- **3 new examples (115–117)** demonstrating SDK 10.7.6708 APIs:
  - 115 (`option_strategy_builder`): Enumerate option strategies, analyze P&L profile (POP, breakeven, greeks), display valid spreads
  - 116 (`option_combo_order`): Place multi-leg combo orders with margin impact check via `comboorder_tradinginfo_query`
  - 117 (`odd_lot_book`): Subscribe to odd-lot order books and compare with normal order books
- New enums: `OrderBookType`, `OptionStrategyType` (14 types), `StrategyLegAction`, `PositionType`, `TimeInForce.GTD`, `SubType.ORDER_BOOK_ODD`
- New markets: `Market.SG`, `Market.MY`, `Market.JP` (equities)

### Changed

- `requirements.txt`: `futu-api>=5.0.0` → `>=10.7.6708`
- `pyproject.toml`: `dependencies` now requires `futu-api>=10.7.6708`
- `position_list_query` / `order_list_query` / `history_order_list_query` — new columns auto-appear: `combo_id`, `strategy_type`, `position_type`, `expire_time`, `amount`, `combo_legs`
- All doc version strings updated to `10.7.6708`

### Fixed

- Zero breaking changes detected — all 114 existing examples compatible with SDK 10.7.6708 without modification
- `connect.py` `RetCode` shim remains in place (SDK 10.7 still does not have `ft.RetCode`)

## [1.8.0] — 2026-05-24

### Added

- **8 new composite examples (107–114)** combining multiple SDK 10.6.6608 APIs into integrated analysis workflows:
  - 107 (`earnings_surprise`): Multi-source earnings dashboard — IV crush, price move heatmap, analyst consensus sweep, surprise score
  - 108 (`short_squeeze`): Short squeeze risk scanner — short interest, daily short volume, utilization ratio → composite score
  - 109 (`insider_monitor`): Insider activity aggregation — net ratio, trade signal, executive roster with insider trades
  - 110 (`dividend_calendar`): Dividend capture calendar — upcoming dividends, ex-dates, stock splits, rights issues, yield analysis
  - 111 (`company_health`): 4-dimension health score (management, efficiency, financials, profile) with ASCII bar chart
  - 112 (`option_flow`): Option screener with volume/OI/IV filters, flow score, drilldown into vol and exercise probability
  - 113 (`institutional_flow`): Institutional holder tracking — top holders, quantity changes, accumulators/distributors
  - 114 (`valuation_heatmap`): PE percentile, z-score vs 3-year mean, market distribution histogram, valuation signal

### Changed

- Updated `examples/README.md` and `README.md` — 106 → 114 example index
- Updated `scripts/run_all.py` — added all 8 new examples to SLOW_EXAMPLES (45s each)

## [1.7.0] — 2026-05-23

### Added

- **SDK 10.6.6608 upgrade** — upgraded from Futu OpenAPI SDK 10.5.6508 to 10.6.6608. 30 new APIs added by the SDK, 5 removed APIs handled.
- **8 new examples (99–106)** demonstrating 30+ new SDK APIs:
  - 99 (`financial_statements`): `get_financials_statements`, `get_financials_revenue_breakdown`, `get_financials_earnings_price_move`, `get_financials_earnings_price_history`
  - 100 (`research_ratings`): `get_research_analyst_consensus`, `get_research_rating_summary`, `get_research_morningstar_report`
  - 101 (`company_fundamentals`): `get_company_profile`, `get_company_executives`, `get_company_executive_background`, `get_company_operational_efficiency`
  - 102 (`shareholders_insiders`): `get_shareholders_overview`, `get_shareholders_holding_changes`, `get_shareholders_holder_detail`, `get_shareholders_institutional`, `get_insider_holder_list`, `get_insider_trade_list`
  - 103 (`corporate_actions`): `get_corporate_actions_dividends`, `get_corporate_actions_buybacks`, `get_corporate_actions_stock_splits`
  - 104 (`short_volume_interest`): `get_short_interest`, `get_daily_short_volume`, `get_top_ten_buy_sell_brokers`
  - 105 (`valuation_screener`): `get_valuation_detail`, `get_valuation_plate_stock_list`, `get_stock_screen`
  - 106 (`option_analytics`): `get_option_volatility`, `get_option_exercise_probability`, `get_option_screen`

### Fixed

- **6 examples updated** for SDK 10.6.6608 API compatibility:
  - `94_earnings_analyzer`: replaced `get_financial_report`/`get_income_statement` with `get_financials_statements`; replaced `get_stock_list` with `get_stock_basicinfo(…, stock_type=…)`
  - `86_market_breadth`, `89_gap_scanner`, `95_52week_scanner`: replaced `get_stock_list(…)` with `get_stock_basicinfo(…, stock_type=ft.SecurityType.STOCK)`
  - `83_dividend_tracker`: removed `get_code_change_history` block (API removed, no replacement)
  - `75_futures_term_structure`: replaced `get_instrument_info(code)` with `get_future_info([code])`
- **8 new examples (99–106) fixed** during testing against upgraded OpenD:
  - Added `ft.RetCode` compatibility shim in `connect.py` (SDK 10.6.6608 removed this class, broken 115 references)
  - Fixed `get_financials_statements` parameter types (uses int enums, not strings)
  - Fixed 3-tuple unpacking for `get_short_interest`/`get_daily_short_volume`
  - Fixed `get_stock_screen`/`get_option_screen` to use protobuf request builders
  - Fixed `get_valuation_plate_stock_list` to accept stock code (not market enum)
  - Added dict/DataFrame dual-type `show()` helper for APIs returning mixed types

### Changed

- Added `7/8/9` prefixes to `run_all.py` directory discovery filter for examples 70–106
- All documentation updated to reflect 106 total examples and SDK 10.6.6608

---

## [1.6.0] — 2026-05-16

### Added

- **Health monitoring + auto-failover** (`examples/connect.py`): background daemon thread pings the active gateway every 15s via `get_global_state()`. On N consecutive failures, automatically fails over to the next-best host. Configurable via `health_monitor=True` kwarg on `create_quote_context()` / `create_trade_context()`.
- **Retry with fallback chain**: `connect_opend()` now tries every reachable host (not just the fastest) before raising, with configurable exponential backoff (`retry_count`, `backoff_base` params).
- **Lifecycle hooks**: new `ConnectionHooks` dataclass with `on_connect`, `on_failover`, `on_disconnect`, `on_heartbeat` callbacks. Pass via `hooks=` kwarg.
- **New example 98 (`ha_diagnostics`)**: interactive HA diagnostic tool that shows ranked host list, real-time heartbeats, failover detection, and connection statistics.
- **Example 00 updated**: now demonstrates health monitoring with 3 heartbeat samples after connecting.

### Changed

- `connect_opend()` now returns 3-tuple `(info_dict, actual_rsa, ranked_hosts)` instead of 2-tuple — internal change, no caller impact.
- `clear_connection_cache()` now also stops the health monitor thread.
- `connect.py` now imports `threading` and `dataclasses` (stdlib, no new dependencies).

### Fixed

- Previous single-host-failure-only fallback now tries all ranked hosts before raising.

---

## [1.0.0] — 2026-05-14

### Added

- **58 examples** (`00_connect_ha` through `57_vwap_benchmark`) covering the full Futu OpenAPI surface
- **HA gateway selection** (`examples/connect.py`) — parallel TCP probe, latency-sorted, RSA auto-fallback with shared connection cache between quote and trade contexts
- **10+ SDK API patterns** demonstrated: snapshots, K-lines, tickers, order books, broker queues, option chains, warrants, capital flow, MACD strategy, trade lifecycle, push handlers, advanced real-time analytics
- **Full test suite** (`scripts/run_all.py`) — automated PASS/FAIL runner with push-loop and trade-lockout detection
- **Comprehensive SDK quirk documentation** (`AGENTS.md`) — return type deviations, non-existent enums, pandas traps verified against a live gateway

### Fixed

- `subscribe()` / `unsubscribe()` return tuple unpacking across all examples
- `get_broker_queue()` return value unpacking
- `get_option_chain()` parameter ordering in example 52
- Thread safety in `44_multi_market_snapshot`
- Infinite retry loops in `06_stock_sell`
- `SysNotifyHandlerBase` content type handling
- `connect.py` resource leak — `ctx.close()` moved to `finally`
- Column name `name` → `plate_name` in `13_plate`
- `set_futu_debug_model(True)` removed from push examples

### Documentation

- `README.md`, `CHANGELOG.md`, `ARCHITECTURE.md`, `CONTRIBUTING.md`, `TROUBLESHOOTING.md`, `AGENTS.md`

---

## [1.1.0] — [1.5.0] — 2026-05-14

**39 advanced examples added (v1.1.0–v1.5.0).** All implementation plans complete.

| Range | Count | Highlights |
|-------|-------|------------|
| v1.1.0 (58–67) | 10 | Options Greeks, Dark Pool Detector, Cross-Market Arb, TWAP Slicer, Portfolio Risk, Earnings Screener, Backtesting, Vol Surface, Multi-Leg Order, Health Monitor |
| v1.2.0 (68–77) | 10 | Trailing Stop, Bollinger Bounce, Warrant Valuation, Market Regime, Candlestick Scanner, Correlation Tracker, OrderFlow Viz, Futures Term Structure, Kelly Sizer, Iceberg Detector |
| v1.3.0 (78–82) | 5 | Grid Trading, Pairs Trading, Multi-Leg Options, Portfolio Rebalance, Unusual Options |
| v1.4.0 (83–87) | 5 | Dividend Tracker, VWAP Analysis, Vol Skew, Market Breadth, Watchlist Alerts |
| v1.5.0 (88–97) | 10 | SL/TP Engine, Gap Scanner, AH Premium, Sector Rotation, Monte Carlo, Calendar Spread, Earnings Analyzer, 52-Week Scanner, Margin Monitor, VWAP Anchored |

### Bug Fixes (v1.1.0+)

- `55_momentum_screener` — `start=None` → `start=""`
- TROUBLESHOOTING.md — duplicate Daily section removed

### Documentation (v1.1.0+)

- All doc files updated for 97-example count
- `TROUBLESHOOTING.md` — expanded to 290 lines covering connection, RSA, trade lockout, quota, pandas pitfalls
- `examples/README.md` — full categorized 97-example index with descriptions