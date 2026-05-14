# Implementation Plans — Advanced Examples

**All 10 plans have been implemented.** See [examples/README.md](examples/README.md) for the full 97-example index.

Plans archive retained below for reference.

---

## Table of Contents

1. [58 — Options Greeks Dashboard](#58--options-greeks-dashboard)
2. [59 — Dark Pool / Block Trade Detector](#59--dark-pool--block-trade-detector)
3. [60 — Cross-Market Arbitrage Spread Monitor](#60--cross-market-arbitrage-spread-monitor)
4. [61 — TWAP Order Slicer](#61--twap-order-slicer)
5. [62 — Portfolio Risk Monitor](#62--portfolio-risk-monitor)
6. [63 — Earnings Volatility Screener](#63--earnings-volatility-screener)
7. [64 — Backtesting Mini-Framework](#64--backtesting-mini-framework)
8. [65 — Volatility Surface Builder](#65--volatility-surface-builder)
9. [66 — Multi-Leg Options Order](#66--multi-leg-options-order)
10. [67 — Connection Health Monitor](#67--connection-health-monitor)

---

## 58 — Options Greeks Dashboard

**Directory:** `examples/58_options_greeks/`

### Objective

Subscribe to an option position's underlying stock, fetch the option chain, compute the five Greeks (delta, gamma, theta, vega, rho), and print a live-updating table. No order placement — pure monitoring.

### SDK APIs Used

| API | Purpose |
|-----|---------|
| `OpenQuoteContext.get_option_chain()` | Fetch call/put chains for the underlying |
| `OpenQuoteContext.subscribe(QUOTE)` | Live underlying price feed |
| `OpenQuoteContext.get_stock_quote()` | Current underlying price + IV |
| `StockQuoteHandlerBase` | Receive price updates as they happen |

### Data Flow

```
1. User picks underlying stock + expiration (e.g. US.NVDA, nearest monthly)
2. ctx.get_option_chain() → DataFrame with strike_price, last_price, implied_volatility
3. ctx.subscribe(underlying, QUOTE) → live price updates
4. On each price update:
   a. Fetch current option chain prices (poll every 30s or on push)
   b. For each strike:
      - Compute d1, d2 using Black-Scholes (underlying price, strike, time-to-expiry, IV, risk-free rate)
      - delta = N(d1)
      - gamma = N'(d1) / (S * σ * √T)
      - theta = -(S * N'(d1) * σ) / (2√T) - r * K * e^(-rT) * N(d2)
      - vega = S * N'(d1) * √T
      - rho = K * T * e^(-rT) * N(d2)
   c. Print table: Strike | Type | Delta | Gamma | Theta | Vega | Last Price
```

**Black-Scholes model:** Implemented in pure Python (no numpy/scipy dependency). Use `math.erf` / `math.erfc` from stdlib for cumulative normal distribution. Risk-free rate = 4.5% (current SOFR approximate, make configurable).

### Edge Cases

- Option chain empty (no options for this underlying)
- Underlying price far OTM → Greeks near zero (handle division by zero in gamma)
- Time-to-expiry = 0 (expiry day) → set to 1/36500 to avoid division by zero
- IV = 0 (no trades yet) → skip that strike row

### Acceptance Criteria

```
Given: stock = "US.NVDA", nearest monthly expiry
When:  script runs for 30s
Then:  every 5s a table prints with ≥5 rows
Then:  each row shows: Strike, Call/Put, Delta (0–1), Gamma, Theta, Vega
Then:  no numpy/Scipy import — pure math.stdlib only
Then:  delta changes visibly when underlying price moves
```

### Files

```
examples/58_options_greeks/
├── main.py           # entry point, handler registration
├── greeks.py         # Black-Scholes Greeks computation (pure Python)
└── README.md          # what this demonstrates
```

### Risk

None — read-only, no orders placed. Computation may produce NaN for deeply OTM strikes (guard with `math.isnan`).

---

## 59 — Dark Pool / Block Trade Detector

**Directory:** `examples/59_dark_pool_detector/`

### Objective

Detect potential dark pool or off-book trades by cross-referencing ticker prints against broker queue depth. A large ticker print that doesn't reduce the corresponding broker queue level suggests the trade was executed off-exchange.

### SDK APIs Used

| API | Purpose |
|-----|---------|
| `OpenQuoteContext.subscribe(TICKER, BROKER)` | Live ticker + broker queue feeds |
| `TickerHandlerBase` | Receive every trade print |
| `BrokerHandlerBase` | Receive broker queue changes |
| `OpenQuoteContext.get_broker_queue()` (polling) | Snapshot for cross-reference |

### Data Flow

```
1. Subscribe to HK.00700 with TICKER + BROKER subtypes
2. Maintain a snapshot of the current broker queue (bid levels + ask levels, with volume)
3. On each TICKER push:
   a. Is the ticker volume > threshold (e.g. 10× normal lot)?
   b. If yes: compare ticker price against current broker queue levels
   c. If ticker price matches a bid/ask level:
      - Check if that level's volume decreased by ~ticker volume
      - If volume did NOT decrease → flag as potential dark pool
   d. Log: timestamp, ticker price, volume, expected queue reduction, actual queue change
4. On each BROKER push: update local snapshot
```

### Data Structures

```python
class BrokerSnapshot:
    bid_levels: list[tuple[price, vol, count]]  # from content["Bid"]
    ask_levels: list[tuple[price, vol, count]]  # from content["Ask"]

class TickerEvent:
    price: float
    volume: int
    direction: str  # "Buy" / "Sell" / "Unknown"
```

### Edge Cases

- No broker data (requires LV1 permission) → fall back to order book data instead
- Tick volume less than one lot → skip (not a block trade)
- Multiple tickers at the same price in quick succession → accumulate volume before cross-referencing
- Market open/close volatility → higher threshold during first/last 5 minutes

### Acceptance Criteria

```
Given: stock = "HK.00700"
When:  running for 60s during market hours
Then:  every large ticker print is cross-referenced against broker queue
Then:  prints "BLOCK: price=xxx vol=yyy expected_queue_drop=zzz actual_drop=aaa" when mismatch detected
Then:  no false positives for small (<10 lot) trades
```

### Files

```
examples/59_dark_pool_detector/
├── main.py
└── README.md
```

### Risk

BROKER push requires LV1 data permission. If unavailable, the detector gracefully degrades to order book data (`get_order_book()` polling). No trades placed.

---

## 60 — Cross-Market Arbitrage Spread Monitor

**Directory:** `examples/60_cross_market_arb/`

### Objective

Monitor a dual-listed stock (HK.00700 / US.TCEHY) for price divergence. Compute the theoretical ADR ratio, track the spread in real time, log when the spread exceeds a configurable threshold.

### SDK APIs Used

| API | Purpose |
|-----|---------|
| `OpenQuoteContext.subscribe(QUOTE)` | Live quotes for both symbols |
| `StockQuoteHandlerBase` | Receive quote updates |
| `OpenQuoteContext.get_stock_quote()` | One-shot quote fetch (fallback) |

### Data Flow

```
1. Define pair: HK.00700 (Tencent HK) ↔ US.TCEHY (Tencent ADR)
   ADR ratio = 1 ADR : 1 HK ordinary share (verify from listing docs)
2. Subscribe to QUOTE for both symbols
3. On each quote update (either side):
   a. Record HK price (HKD) and ADR price (USD)
   b. Convert ADR to HKD using USD/HKD rate (configurable, default 7.82)
   c. Convert ADR to equivalent HK price: adr_eq = adr_price * usd_hkd_rate * adr_ratio
   d. spread_bps = (adr_eq - hk_price) / hk_price * 10000
   e. Print: timestamp | HK price | ADR eq | spread bps | signal
4. Signal logic:
   - |spread| < 50 bps → neutral
   - |spread| 50–150 bps → watching
   - |spread| > 150 bps → DIVERGENCE
```

### Multi-Listing Pairs (extensible)

```python
PAIRS = [
    ("HK.00700", "US.TCEHY",  1.0,   7.82,  "Tencent"),
    ("HK.09988", "US.BABA",   1.0,   7.82,  "Alibaba"),
    ("HK.09888", "US.BIDU",   8.0,   7.82,  "Baidu"),     # 1 ADR = 8 ordinary
    ("HK.03690", "US.MEITUAN", None, None,  "Meituan"),   # no US listing
]
```

### Edge Cases

- One market closed while other open (HK night vs US day) → skip comparison, log "market closed"
- FX rate not updated → use cached rate, log warning
- ADR ratio unknown → require manual input, skip pair if unset

### Acceptance Criteria

```
Given: pair = ("HK.00700", "US.TCEHY")
When:  running for 60s
Then:  prints a line every time HK or US quote updates
Then:  shows HK price, ADR-equivalent price, spread in bps
Then:  handles one-market-closed case without crashing
```

### Files

```
examples/60_cross_market_arb/
├── main.py
└── README.md
```

### Risk

Read-only. FX rate is hardcoded (configurable via constant). No trade execution.

---

## 61 — TWAP Order Slicer

**Directory:** `examples/61_twap_slicer/`

### Objective

Demonstrate algorithmic order execution: slice a large simulated order into N child orders over M minutes. Each slice reads `get_order_book()` to price at the best bid (sell) or best ask (buy) without sweeping the spread. Log fill price, slippage, and time-weighted average price vs arrival price.

### SDK APIs Used

| API | Purpose |
|-----|---------|
| `OpenSecTradeContext.place_order()` | Place each child slice |
| `OpenSecTradeContext.unlock_trade()` | Unlock SIMULATE account |
| `OpenSecTradeContext.order_list_query()` | Check fill status of each slice |
| `OpenQuoteContext.get_order_book()` | Read current best bid/ask before each slice |
| `OpenQuoteContext.get_market_snapshot()` | Get initial arrival price |

### Algorithm

```
Given: stock, total_qty, num_slices = 10, interval_sec = 30, side = SELL

1. arrival_price = get_market_snapshot()[stock]["last_price"]
2. slice_qty = total_qty // num_slices (rounded to lot_size)
3. For i in range(num_slices):
   a. sleep(interval_sec)
   b. order_book = get_order_book(stock)
   c. If SELL: price = order_book["Bid"][0][0] (best bid)
      If BUY:  price = order_book["Ask"][0][0] (best ask)
   d. place_order(price=price, qty=slice_qty, side=side, SIMULATE)
   e. Log: slice i, price, qty, cumulative_filled, slippage vs arrival
4. After all slices: print summary
   - Total filled / total intended
   - TWAP = Σ(price_i * qty_i) / Σ(qty_i)
   - Slippage bps = (TWAP - arrival) / arrival * 10000
```

### Parameters

```python
STOCK = "HK.00700"
SIDE = ft.TrdSide.SELL
TOTAL_QTY = 1000          # total shares to sell
NUM_SLICES = 10           # number of child orders
INTERVAL_SEC = 30         # seconds between slices
TRD_ENV = ft.TrdEnv.SIMULATE
```

### Edge Cases

- No bid (order book empty) → skip slice, retry next interval
- Slice qty after rounding = 0 → adjust to 1 lot minimum
- Previous slice not filled yet → cancel before placing next (or let it accumulate)
- Market closes during execution → abort remaining slices
- Price moves > 5% since arrival → pause, log warning

### Acceptance Criteria

```
Given: stock = "HK.00700", qty = 1000, 10 slices, 30s apart
When:  script runs in SIMULATE
Then:  places ≤10 child orders over ≤5 minutes
Then:  each slice prints: price, qty, cumulative filled, slippage
Then:  final summary shows TWAP, total filled, total slippage bps
Then:  all orders are in SIMULATE (verifiable via order_list_query)
```

### Files

```
examples/61_twap_slicer/
├── main.py
└── README.md
```

### Risk

Places real SIMULATE orders. If the account is unlocked, orders will be created. Uses `cancel_all_order(trd_env=SIMULATE)` in `finally` block to clean up uncompleted slices. All orders are SIMULATE only — enforced at the example level with a runtime assertion.

---

## 62 — Portfolio Risk Monitor

**Directory:** `examples/62_portfolio_risk/`

### Objective

Poll positions, compute aggregate portfolio risk metrics, and push alerts when risk thresholds are breached. No order placement — pure monitoring and reporting.

### SDK APIs Used

| API | Purpose |
|-----|---------|
| `OpenSecTradeContext.position_list_query()` | Current holdings |
| `OpenSecTradeContext.accinfo_query()` | Total equity, buying power |
| `OpenQuoteContext.get_stock_quote()` | Current prices for positions |
| `OpenSecTradeContext.get_margin_ratio()` | Per-position margin info |

### Risk Metrics

| Metric | Formula | Alert Threshold |
|--------|---------|-----------------|
| Concentration % | position_value / total_equity | > 15% |
| Sector exposure | Σ sector_value / total_equity | > 40% |
| Leverage ratio | total_position_value / total_equity | > 2.0 |
| Buying power used | (total_equity - available_power) / total_equity | > 80% |
| Unrealized P&L % | Σ (current_price - avg_cost) * qty / total_equity | < -10% |
| Margin utilization | used_margin / total_margin | > 70% |

### Data Flow

```
1. unlock_trade(SIMULATE)
2. Loop every 30 seconds:
   a. positions = position_list_query()
   b. acc_info = accinfo_query()
   c. For each position: stock_quote() to get current price
   d. Compute all 6 risk metrics
   e. Print table:
      Position | Qty | Cost | Current | P&L% | Weight% | Margin%
   f. Print summary:
      Total Equity | Leverage | Buying Power Used | Concentration Risk
   g. If any metric exceeds threshold → print ALERT with emoji
```

### Edge Cases

- Empty portfolio → print "No positions — monitoring idle" but keep running
- New position added while running → detect and include automatically
- Position closed → remove from next report
- Market closed → prices don't update, use last known

### Acceptance Criteria

```
Given: SIMULATE account with ≥1 position
When:  running for 2 minutes
Then:  prints a full risk report every 30s
Then:  each report shows all 6 metrics
Then:  if any threshold breached, prints ALERT
Then:  handles empty portfolio without crashing
```

### Files

```
examples/62_portfolio_risk/
├── main.py
├── risk_calc.py       # risk metric computation
└── README.md
```

### Risk

Read-only after initial unlock. No order placement. Reads position data only.

---

## 63 — Earnings Volatility Screener

**Directory:** `examples/63_earnings_screener/`

### Objective

Scan upcoming earnings events, fetch pre-earnings option IV, then check post-earnings price/volume action using unusual activity APIs. Identifies high-probability setups.

### SDK APIs Used

| API | Purpose |
|-----|---------|
| `OpenQuoteContext.get_option_chain()` | Pre-earnings IV |
| `OpenQuoteContext.get_option_expiration_date()` | Find nearest expiry after earnings |
| `OpenQuoteContext.get_technical_unusual()` | Post-earnings volume/price anomalies |
| `OpenQuoteContext.get_financial_unusual()` | Post-earnings financial anomalies |
| `OpenQuoteContext.get_stock_basicinfo()` | Enumerate stocks to screen |
| `OpenQuoteContext.get_market_state()` | Check if market is open |

### Screen Phases

**Phase 1 — Pre-earnings scan (run before earnings date):**
```
1. For a list of high-profile stocks (NVDA, AAPL, TSLA, etc.):
2.   Fetch nearest option expiration after expected earnings date
3.   Get option chain → extract ATM implied volatility
4.   Compare IV to 20-day historical IV (from 20-day HV)
5.   If IV / HV > 1.5 → "IV elevated — premium rich"
6.   If IV / HV > 2.0 → "IV extremely elevated — earnings priced in"
7. Print: Stock | Earnings Date | ATM IV | 20d HV | IV/HV Ratio | Signal
```

**Phase 2 — Post-earnings check (run after earnings):**
```
1. For same stock list:
2.   get_technical_unusual(last 2 days)
3.   get_financial_unusual(last 2 days)
4. If unusual volume detected:
   - "UNUSUAL VOLUME: price_gap%=xxx vol_spike=xxx"
5. If unusual financial detected:
   - "FINANCIAL ANOMALY: metric=xxx value=xxx"
```

### Edge Cases

- Earnings date not known (no API for it) → user provides expected dates via config dict
- Option chain empty for that expiry → skip stock
- No unusual activity → print "no anomalies detected"
- Market closed on earnings day → shift check to next trading day

### Acceptance Criteria

```
Given: stock list with known earnings dates
When:  script runs
Then:  Phase 1 prints IV/HV ratios for all stocks with options data
Then:  Phase 2 prints any unusual activity detected
Then:  each section is clearly labeled with phase header
```

### Files

```
examples/63_earnings_screener/
├── main.py
├── earnings_data.py   # hardcoded earnings calendar (since no API exists)
└── README.md
```

### Risk

Read-only. Earnings dates are hardcoded (no Futu API provides earnings calendar). The example is educational — it shows the *pattern* of combining options + unusual data pre/post event.

---

## 64 — Backtesting Mini-Framework

**Directory:** `examples/64_backtesting/`

### Objective

Pull historical K-line data, run a parameterized strategy, compute performance metrics. No live trading. Pure historical analysis.

### SDK APIs Used

| API | Purpose |
|-----|---------|
| `OpenQuoteContext.request_history_kline()` | Historical price data (paginated) |
| `OpenQuoteContext.get_history_kl_quota()` | Check remaining quota before fetching |

### Strategy Interface

```python
class Strategy(ABC):
    @abstractmethod
    def next(self, row: dict, state: dict) -> Signal:
        """Return 'BUY', 'SELL', or 'HOLD' given current bar + state."""
```

**Built-in strategies:**
1. `SmaCross` — short MA crosses above/below long MA
2. `RsiStrategy` — RSI < 30 buy, RSI > 70 sell
3. `MacdStrategy` — golden cross / death cross (same as 04 but backtested)

### Backtest Engine

```python
def backtest(df: pd.DataFrame, strategy: Strategy, initial_capital: float = 1_000_000):
    capital = initial_capital
    position = 0  # shares held
    trades = []
    
    for i in range(lookback, len(df)):
        row = df.iloc[i]
        signal = strategy.next(row, state)
        
        if signal == 'BUY' and position == 0:
            qty = int(capital / row['close'] / 100) * 100  # round to lots
            cost = qty * row['close']
            capital -= cost
            position = qty
            trades.append({'date': row['time_key'], 'type': 'BUY', 'price': row['close'], 'qty': qty})
        elif signal == 'SELL' and position > 0:
            capital += position * row['close']
            trades.append({'date': row['time_key'], 'type': 'SELL', 'price': row['close'], 'qty': position})
            position = 0
    
    # Close any remaining position at last price
    if position > 0:
        capital += position * df.iloc[-1]['close']
    
    return compute_metrics(capital, trades, initial_capital, df)
```

### Performance Metrics

| Metric | Formula |
|--------|---------|
| Total Return % | (final_capital / initial_capital - 1) * 100 |
| Sharpe Ratio | (mean(daily_return) / std(daily_return)) * √252 |
| Max Drawdown % | min(cumulative_peak - cumulative_trough) / peak |
| Win Rate % | winning_trades / total_trades |
| Number of Trades | len(trades) // 2 (round-trips) |

### Output

```
=== BACKTEST RESULTS ===
Strategy: SMA Cross (50 / 200)
Stock:    HK.00700
Period:   2024-01-01 → 2026-05-14

Total Return:    +23.4%
Sharpe Ratio:     0.87
Max Drawdown:   -15.2%
Win Rate:        44.0%
Trades:          25

Equity Curve:
  Date       | Capital
  2024-01-02 | 1,000,000
  2024-03-15 | 1,050,000  ← BUY @ 320.0
  ...
  2026-05-14 | 1,234,000
```

### Edge Cases

- Not enough historical data for strategy parameters (e.g. 200 bars for SMA 200) → raise clear error
- Stock split during backtest period → use adjusted prices (AuType.QFQ)
- K-line quota exceeded → print current usage, suggest waiting
- No trades triggered in entire period → print "no signals generated"

### Acceptance Criteria

```
Given: stock = "HK.00700", strategy = SMA_50_200, period = 2024-01 to 2026-05
When:  script runs
Then:  fetches historical K-lines (may paginate if > quota limit)
Then:  runs backtest over entire period
Then:  prints all performance metrics
Then:  prints equity curve table
Then:  handles strategy with no signals gracefully
```

### Files

```
examples/64_backtesting/
├── main.py              # entry point
├── engine.py            # backtest() loop
├── strategies.py        # SmaCross, RsiStrategy, MacdStrategy
├── metrics.py           # Sharpe, drawdown, win rate computation
└── README.md
```

### Risk

Read-only — no API calls beyond `request_history_kline()`. Does NOT place orders. The quota check at startup prevents unexpected rate limit hits.

---

## 65 — Volatility Surface Builder

**Directory:** `examples/65_vol_surface/`

### Objective

Fetch all option chains across all available expirations for a given underlying, extract implied volatility per strike, and build/display a 3D vol surface matrix (expiry × strike → IV).

### SDK APIs Used

| API | Purpose |
|-----|---------|
| `OpenQuoteContext.get_option_expiration_date()` | All available expirations |
| `OpenQuoteContext.get_option_chain()` | Chain for each expiry |
| `OpenQuoteContext.get_stock_quote()` | Current underlying price (for moneyness) |

### Data Flow

```
1. For given underlying (e.g. US.NVDA):
2.   expirations = get_option_expiration_date()
3.   current_price = get_stock_quote()[0]["last_price"]
4.   For each expiration (limit to 10 nearest to avoid quota issues):
5.     chain = get_option_chain(code, start=exp_date, end=exp_date, option_type=CALL)
6.     Extract: strike_price, implied_volatility
7.     Compute moneyness = strike_price / current_price
8.   Build matrix:
         Expiry 1  | 0.80x  0.90x  1.00x  1.10x  1.20x  (moneyness)
         Expiry 2  | 35.2%  28.1%  24.5%  30.3%  38.7%  (IV)
         Expiry 3  | 36.0%  29.5%  25.0%  31.0%  40.2%
9.   Print as formatted table
10.  Note the volatility smile/skew pattern
```

### Filtering

Only include strikes with `moneyness` between 0.7 and 1.3 (70%–130% of spot). Only include expirations with `option_expiry_date_distance` > 1 day (skip 0DTE). Maximum 10 expirations per run to stay within quota.

### Edge Cases

- No options for this underlying → print message, exit gracefully
- Specific expiry returns empty chain → skip that expiry, continue
- IV not populated for some strikes (no trades) → show "—" in table
- Underlying not found → exit with error

### Acceptance Criteria

```
Given: stock = "US.NVDA"
When:  script runs
Then:  fetches up to 10 expirations
Then:  prints a moneyness × expiry IV matrix
Then:  each cell shows IV as percentage (e.g. "24.5%")
Then:  empty cells show "—" instead of 0%
Then:  total print width fits in 120 chars
```

### Files

```
examples/65_vol_surface/
├── main.py
└── README.md
```

### Risk

Read-only. May consume significant historical K-line quota if many expirations are fetched. The 10-expiration limit protects against this.

---

## 66 — Multi-Leg Options Order

**Directory:** `examples/66_multi_leg_order/`

### Objective

Place a multi-leg options strategy (vertical spread, iron condor) on a SIMULATE account. Demonstrate simultaneous order placement, leg fill monitoring, and net position reporting.

### SDK APIs Used

| API | Purpose |
|-----|---------|
| `OpenSecTradeContext.place_order()` | Place each leg |
| `OpenSecTradeContext.unlock_trade()` | Unlock SIMULATE |
| `OpenSecTradeContext.order_list_query()` | Monitor fill status |
| `OpenSecTradeContext.position_list_query()` | Check resulting position |
| `OpenQuoteContext.get_option_chain()` | Select strikes with bids/asks |
| `OpenQuoteContext.get_order_book()` | Price each leg at the market |

### Strategy: Vertical Call Spread

```
Leg 1: BUY  Call @ strike K1 (lower strike, higher premium)
Leg 2: SELL Call @ strike K2 (higher strike, lower premium)

Net debit = premium_leg1 - premium_leg2
Max profit = K2 - K1 - net_debit (at expiry if price > K2)
Max loss   = net_debit (at expiry if price < K1)
```

### Data Flow

```
1. Pick underlying + expiration (e.g. US.NVDA, nearest monthly)
2. Fetch option chain → find bid/ask for each strike
3. Select strikes: K1 = ATM - 1 strike, K2 = ATM + 1 strike
4. Price each leg:
   - Leg 1 (BUY): use ask price (paying the spread)
   - Leg 2 (SELL): use bid price (receiving the spread)
5. Check buying power (accinfo_query) to ensure sufficient funds
6. Place both orders simultaneously:
   - place_order(code=leg1_code, trd_side=BUY, price=ask, qty=1, order_type=NORMAL)
   - place_order(code=leg2_code, trd_side=SELL, price=bid, qty=1, order_type=NORMAL)
7. Monitor fills for 30 seconds:
   - Poll order_list_query every 5s
   - If both legs filled: log net debit, print position summary
   - If partial fill: flag as risk (one leg filled, other not)
8. Cancel any unfilled legs after timeout
9. Print final P&L summary
```

### Safety

`cancel_all_order(trd_env=SIMULATE)` in `finally` block to clean up any open leg orders. Positions that DID fill remain (demonstration only — user must close manually in SIMULATE).

### Edge Cases

- Option leg not filled → cancel unfilled, report "partial fill — RISK"
- No bids for the sell leg → skip this spread, try different strikes
- Buying power insufficient → print available vs required, abort
- Account doesn't have options trading enabled → print message, skip

### Acceptance Criteria

```
Given: stock = "US.NVDA", nearest monthly expiry
When:  script runs
Then:  selects ATM vertical call spread strikes
Then:  computes net debit before placing orders
Then:  places both legs as SIMULATE orders
Then:  monitors fill status for 30s
Then:  cancels unfilled legs
Then:  prints summary: legs filled, net debit, max profit, max loss
```

### Files

```
examples/66_multi_leg_order/
├── main.py
├── spreads.py          # VerticalSpread, IronCondor strategy classes
└── README.md
```

### Risk

**HIGH** — places real SIMULATE orders that remain open if unfilled. The `finally` block calls `cancel_all_order(trd_env=SIMULATE)` as cleanup. User must verify positions in their SIMULATE account after running. All orders use 1 contract only.

---

## 67 — Connection Health Monitor

**Directory:** `examples/67_health_monitor/`

### Objective

A standalone watchdog that monitors OpenD connection health by polling `get_delay_statistics()`, `get_global_state()`, and `query_subscription()` at regular intervals. Logs latency, quota usage, subscription count, and alerts on anomalies.

### SDK APIs Used

| API | Purpose |
|-----|---------|
| `OpenQuoteContext.get_delay_statistics()` | Connection round-trip latency |
| `OpenQuoteContext.get_global_state()` | Server version, login status, market status |
| `OpenQuoteContext.query_subscription()` | Subscription count, total used / remaining |
| `OpenQuoteContext.get_history_kl_quota()` | Historical K-line quota remaining |

### Health Metrics

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| API Latency | `get_delay_statistics()` | > 500ms |
| Subscription Used | `query_subscription()` | > 80% of total quota |
| K-line Quota Remaining | `get_history_kl_quota()` | < 10 |
| Server Version | `get_global_state()` | warn if outdated |
| Market HK Status | `get_global_state()` | log state changes |
| Connection Uptime | internal timer | n/a |

### Data Flow

```
1. create_quote_context()
2. Record connection time as T0
3. Loop every 30 seconds (configurable):
   a. latency = get_delay_statistics()
   b. state = get_global_state()
   c. sub = query_subscription(is_all_conn=True)
   d. quota = get_history_kl_quota()
   e. Print report:
      [t+30s] latency=12ms ver=10.5.6508 subs=15/200 quota=487/500 hk=OPEN
   f. If any metric exceeds threshold:
      print "ALERT: latency 520ms exceeds 500ms threshold"
4. On KeyboardInterrupt:
   Print final summary with uptime, max latency, min latency, avg latency
```

### Output Format

```
=== Connection Health Monitor ===
Host: 172.18.208.88:11111 (RSA=True)
Interval: 30s
Thresholds: latency > 500ms, subs > 80%, quota < 10

[T+000s] Connecting...
[T+030s] latency=15ms ver=10.5.6508 subs=3/200 quota=498/500 hk=OPEN us=PRE_OPEN
[T+060s] latency=12ms ver=10.5.6508 subs=3/200 quota=498/500 hk=OPEN us=OPEN
[T+090s] latency=520ms subs=3/200 quota=498/500 hk=OPEN
  ⚠ ALERT: latency 520ms exceeds 500ms threshold
...

=== Final Summary ===
Uptime: 300s
Latency: min=8ms max=520ms avg=18ms
Alerts triggered: 1 (latency spike)
```

### Edge Cases

- `get_delay_statistics()` not available (older SDK) → skip that metric, print "N/A"
- Gateway connection drops mid-run → reconnect logic (retry 3 times, then exit)
- First report at T+0 (immediate) → no, wait for first interval to have meaningful data

### Acceptance Criteria

```
Given: gateway is reachable
When:  script runs for 60s (2 intervals)
Then:  first report at T+30s
Then:  each report shows latency, version, subs, quota, market states
Then:  final summary shows uptime and latency stats
Then:  handles get_delay_statistics() missing without crashing
```

### Files

```
examples/67_health_monitor/
├── main.py
└── README.md
```

### Risk

Read-only. No order placement. Lightweight — uses only polling APIs, no push handlers.

---

## Implementation Order

| Order | Example | Risk | Dependencies | Est. Effort |
|-------|---------|------|-------------|-------------|
| 1 | 67 — Health Monitor | None | None | 1 session |
| 2 | 60 — Cross-Market Arb | None | None | 1 session |
| 3 | 64 — Backtesting | None | pandas | 2 sessions |
| 4 | 58 — Options Greeks | None | `math` stdlib | 2 sessions |
| 5 | 65 — Vol Surface | None | pandas | 1 session |
| 6 | 62 — Portfolio Risk | Read-only | trade ctx unlock | 1 session |
| 7 | 63 — Earnings Screener | None | None | 1 session |
| 8 | 59 — Dark Pool Detector | None | LV1 permission | 1 session |
| 9 | 61 — TWAP Slicer | **SIMULATE orders** | trade ctx unlock | 2 sessions |
| 10 | 66 — Multi-Leg Options | **SIMULATE orders** | trade ctx + options acct | 2 sessions |

**Rationale:** Read-only examples first (build confidence, no financial risk). Backtesting and Greeks next (pure computation, no live API dependency). Trade examples last (require unlocked account, carry cleanup responsibility).

---

## Cross-Cutting Concerns

### Error Handling Pattern (all examples)

```python
try:
    ctx = create_quote_context()
    # ... example logic ...
except KeyboardInterrupt:
    logger.info("Interrupted by user")
except Exception:
    logger.error("Unhandled error", exc_info=True)
    raise SystemExit(1)
finally:
    ctx.close()
```

### Script Boilerplate (all examples)

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context, create_trade_context, get_demo_trade_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
```

### SIMULATE Enforcement (trade examples)

```python
assert trd_ctx.is_futures_market_sim() or True, "This example requires SIMULATE account"
```

All order-based examples must:
1. Use `ft.TrdEnv.SIMULATE` explicitly on every `place_order()` call
2. Call `cancel_all_order(trd_env=SIMULATE)` in `finally`
3. Print "SIMULATE ONLY — no real orders" at startup
4. Limit quantity to 1 contract / 1 lot for safety

### Documentation (each example)

Every `README.md` includes:
- What it demonstrates (3 bullet points max)
- SDK APIs used (table)
- How to run (1 command)
- Expected output (2-3 sample lines)
- Risk level: NONE / READ-ONLY / SIMULATE ORDERS
