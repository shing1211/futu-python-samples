# Changelog

All notable changes to this project are documented here.

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