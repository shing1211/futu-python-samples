# Changelog

All notable changes to this project are documented here.

---

## [1.0.0] — 2026-05-14

### Added

- **57 new examples** (`00_connect_ha` through `57_vwap_benchmark`) covering the full Futu OpenAPI surface
- **HA gateway selection** (`examples/connect.py`) — parallel TCP probe, latency-sorted, RSA auto-fallback with shared connection cache between quote and trade contexts
- **50+ SDK API patterns** demonstrated: market snapshots, K-lines, tickers, order books, broker queues, option chains, warrants, capital flow, MACD strategy, trade lifecycle, push handlers, and advanced real-time analytics
- **Advanced real-time examples:**
  - `54_pair_trading` — rolling z-score spread via CurKlineHandler
  - `55_momentum_screener` — multi-timeframe RSI + MACD signal confluence
  - `56_order_flow_imbalance` — ORDER_BOOK push accumulation for directional pressure
  - `57_vwap_benchmark` — running VWAP from ticker stream with bps deviation
- **Full test suite** (`scripts/run_all.py`) — automated PASS/FAIL runner with push-loop and trade-lockout detection
- **Comprehensive SDK quirk documentation** (`AGENTS.md`) — return type deviations, non-existent enums, pandas traps, and handler content shapes verified against a live gateway

### Fixed

- `subscribe()` / `unsubscribe()` return tuple unpacking across all examples (SDK returns `(ret_code, None)`, not a bare int)
- `get_broker_queue()` return value unpacking (SDK returns `(ret_code, (bid_df, ask_df))`, not `(ret, bid, ask)`)
- `get_option_chain()` parameter ordering in example 52 (was using positional args mismatched with the API signature)
- Thread safety in `44_multi_market_snapshot` — each thread now creates its own `OpenQuoteContext` instead of sharing one
- Infinite retry loops in `06_stock_sell` — added max-attempt guard to `while True` patterns
- `SysNotifyHandlerBase` content type handling — switched from `on_recv` (string, dict-typed) to `on_recv_rsp` (protobuf, tuple-typed) matching the documented SDK pattern
- `connect.py` resource leak — `ctx.close()` moved to `finally` block in `try_connect()`
- Column name `name` → `plate_name` in `13_plate` matching actual SDK return
- `set_futu_debug_model(True)` removed from push examples (verbose debug output not appropriate for demo scripts)
- `start=None` → `start=""` in `55_momentum_screener` for `request_history_kline()` compatibility

### Documentation

- `README.md` — quick-start guide, configuration reference, connection module docs, full examples index, RSA setup, test suite instructions
- `ARCHITECTURE.md` — system architecture with Mermaid sequence diagrams for all key execution flows: HA connection, quote push, trade lifecycle, MACD strategy, stock screener
- `CONTRIBUTING.md` — example creation template, code conventions, return type reference, pandas pitfall guide, testing instructions
- `TROUBLESHOOTING.md` — connection problems, RSA errors, trade account issues, subscription quota, platform-specific guidance
- `CHANGELOG.md` — this file
- `AGENTS.md` — SDK quirks reference for AI coding tools

## [1.1.0] — 2026-05-14

### Added

- **10 new advanced examples** (58–67) extending into real-time analytics, risk monitoring, and algorithmic execution:

  | # | Example | Category |
  |---|---------|----------|
  | 58 | Options Greeks Dashboard | Computation — Black-Scholes Greeks (delta/gamma/theta/vega/rho) in pure Python |
  | 59 | Dark Pool / Block Trade Detector | Cross-referencing — TICKER + BROKER push for off-book trade detection |
  | 60 | Cross-Market Arbitrage Monitor | Monitoring — HK.00700/US.TCEHY dual-listing spread tracking |
  | 61 | TWAP Order Slicer | Execution — slice large orders over time using ORDER_BOOK pricing |
  | 62 | Portfolio Risk Monitor | Risk — 6 live risk metrics with threshold alerts |
  | 63 | Earnings Volatility Screener | Screening — pre-earnings IV/HV ratio + post-earnings unusual activity |
  | 64 | Backtesting Mini-Framework | Analysis — 3 built-in strategies (SMA, RSI, MACD) with Sharpe/drawdown |
  | 65 | Volatility Surface Builder | Visualization — moneyness × expiry IV matrix from option chains |
  | 66 | Multi-Leg Options Order | Execution — vertical call spread on SIMULATE with fill monitoring |
  | 67 | Connection Health Monitor | Utility — watchdog polling latency, quota, subscriptions, market states |

- `PLANS.md` — detailed implementation plans for all 10 examples covering SDK APIs, data flow, edge cases, acceptance criteria, and risk assessment
- Examples 58, 60, 61, 62, 63, 64, 65, 66, 67, 59 all compile and pass syntax verification
