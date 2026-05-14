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

- `subscribe()` / `unsubscribe()` return tuple unpacking across all examples
- `get_broker_queue()` return value unpacking
- `get_option_chain()` parameter ordering in example 52
- Thread safety in `44_multi_market_snapshot`
- Infinite retry loops in `06_stock_sell`
- `SysNotifyHandlerBase` content type handling
- `connect.py` resource leak — `ctx.close()` moved to `finally`
- Column name `name` → `plate_name` in `13_plate`
- `set_futu_debug_model(True)` removed from push examples
- `start=None` → `start=""` in `55_momentum_screener`

### Documentation

- `README.md`, `ARCHITECTURE.md`, `CONTRIBUTING.md`, `TROUBLESHOOTING.md`, `CHANGELOG.md`, `AGENTS.md`

---

## [1.1.0] — 2026-05-14

### Added

- **10 new advanced examples** (58–67):

  | # | Example | Category |
  |---|---------|----------|
  | 58 | Options Greeks Dashboard | Computation — Black-Scholes Greeks |
  | 59 | Dark Pool / Block Trade Detector | Cross-referencing — TICKER + BROKER push |
  | 60 | Cross-Market Arbitrage Monitor | Monitoring — dual-listing spread tracking |
  | 61 | TWAP Order Slicer | Execution — slice large orders over time |
  | 62 | Portfolio Risk Monitor | Risk — 6 live risk metrics with threshold alerts |
  | 63 | Earnings Volatility Screener | Screening — pre-earnings IV/HV ratio |
  | 64 | Backtesting Mini-Framework | Analysis — SMA, RSI, MACD with Sharpe/drawdown |
  | 65 | Volatility Surface Builder | Visualization — moneyness × expiry IV matrix |
  | 66 | Multi-Leg Options Order | Execution — vertical call spread on SIMULATE |
  | 67 | Connection Health Monitor | Utility — watchdog polling latency, quota |

- `PLANS.md` — detailed implementation plans for all 10 examples

---

## [1.2.0] — 2026-05-14

### Added

- **10 new advanced examples** (68–77):

  | # | Example | Category |
  |---|---------|----------|
  | 68 | Trailing Stop Execution | Execution — dynamic stop-loss with order replacement |
  | 69 | Bollinger Band Bounce | Execution — mean-reversion via pure-Python statistics |
  | 70 | Warrant Valuation Dashboard | Analytics — intrinsic/time value, BSM implied vol ranking |
  | 71 | Market Regime Detector | Analytics — ADX + rolling vol |
  | 72 | Candlestick Pattern Scanner | Screening — 9 classic patterns with confidence scoring |
  | 73 | Multi-Asset Correlation Tracker | Analytics — rolling Pearson matrix |
  | 74 | Order Flow Imbalance Visualizer | Microstructure — real-time ASCII imbalance chart |
  | 75 | Futures Term Structure & Roll Yield | Analytics — dynamic futures discovery |
  | 76 | Kelly Criterion Position Sizer | Risk — optimal sizing with half/quarter-Kelly |
  | 77 | Iceberg Order Detector | Microstructure — heuristic hidden order detection |

---

## [1.3.0] — 2026-05-14

### Added

- **5 new examples** (78–82):

  | # | Example | Category |
  |---|---------|----------|
  | 78 | Grid Trading Bot | Execution — automated buy-low/sell-high grid |
  | 79 | Pairs Trading (Cointegration) | Execution — Engle-Granger stat-arb |
  | 80 | Multi-Leg Options Strategy | Execution — straddle, strangle, iron condor |
  | 81 | Portfolio Rebalancing Bot | Risk — periodic target-allocation rebalancing |
  | 82 | Unusual Options Activity Scanner | Screening — volume anomaly flagging |

---

## [1.4.0] — 2026-05-14

### Added

- **5 new examples** (83–87):

  | # | Example | Category |
  |---|---------|----------|
  | 83 | Dividend & Corporate Action Tracker | Screening — dividends, ex-dates, splits |
  | 84 | VWAP Execution Analysis | Analysis — trade quality vs VWAP benchmark |
  | 85 | Options Volatility Skew Scanner | Screening — IV surface, Newton-Raphson solver |
  | 86 | Market Breadth Dashboard | Analytics — Adv/Dec, McClellan Oscillator |
  | 87 | Smart Watchlist with Alerts | Monitoring — price/RSI/Bollinger alerts |

---

## [1.5.0] — 2026-05-14

### Added

- **10 new examples** (88–97):

  | # | Example | Category |
  |---|---------|----------|
  | 88 | Stop-Loss / Take-Profit Engine | Risk — dual SL/TP with partial exits |
  | 89 | Gap Scanner | Screening — overnight gap detection |
  | 90 | AH Premium/Discount Tracker | Cross-Market — A-share vs H-share comparison |
  | 91 | Sector Rotation Scanner | Screening — RSI-based sector ranking |
  | 92 | Monte Carlo Portfolio Simulator | Risk Analysis — 10K path VaR simulation |
  | 93 | Options Calendar Spread Builder | Options — neutral theta plays via vol differential |
  | 94 | Earnings Surprise Analyzer | Event-Driven — EPS surprise + post-earnings activity |
  | 95 | 52-Week High/Low Scanner | Screening — proximity to yearly extremes |
  | 96 | Margin Utilization Monitor | Risk — real-time margin + liquidation price |
  | 97 | VWAP Anchored Trading Levels | Execution — VWAP-based support/resistance signals |

- Updated README.md, examples/README.md, ARCHITECTURE.md with full 97-example index
- All examples pass `python3 -m py_compile`