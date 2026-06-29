# Advanced Composite Examples — SDK 10.8.6808

**Date:** 2026-06-29
**SDK:** `futu-api>=10.8.6808`
**Series:** Examples 107–114
**Status:** Design phase — not yet implemented

## Overview

Eight composite examples that combine multiple new SDK 10.8.6808 APIs into
non-trivial analysis flows. Each example demonstrates a real-world trading or
research workflow by chaining 2–6 API calls with data transformation logic.

| # | Name | APIs | Theme |
|---|------|------|-------|
| 107 | Earnings Surprise Dashboard | 4 | Financials + Research |
| 108 | Short Squeeze Risk Scanner | 3 | Short Volume + Brokers |
| 109 | Insider Activity Monitor | 4 | Shareholders + Insiders |
| 110 | Dividend Capture Calendar | 3 | Corporate Actions |
| 111 | Company Health Score | 4 | Fundamentals + Financials |
| 112 | Option Flow Screener | 3 | Options Vol + Screen |
| 113 | Institutional Flow Tracker | 4 | Shareholders + Brokers |
| 114 | Valuation Heat Map | 3 | Valuation + Screener |

---

## Design Constraints (all examples)

### Boilerplate (every main.py)

```python
import sys, time, json, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
```

### Return Type Matrix (critical for correct unpacking)

| Return Pattern | How to Unpack | Which APIs |
|----------------|---------------|------------|
| `(RET_OK, DataFrame)` | `ret, df = ctx.api(...)` | earnings_price_move, earnings_price_history, top_ten_buy_sell_brokers, shareholders_holding_changes, shareholders_institutional, insider_trade_list, insider_holder_list, option_volatility, option_exercise_probability, company_profile, company_executives |
| `(RET_OK, raw_dict)` | `ret, data = ctx.api(...)` | financials_statements, research_analyst_consensus, corporate_actions_dividends, corporate_actions_stock_splits, valuation_detail, company_executive_background, company_operational_efficiency |
| `(RET_OK, us_df, hk_df)` | `ret, us_df, hk_df = ctx.api(...)` | get_short_interest, get_daily_short_volume |
| `(RET_OK, dict)` with nested DataFrames | `ret, d = ctx.api(...)`; `d["hk_buy_back_list"]` | corporate_actions_buybacks |
| `(RET_OK, (last_page, all_count, DataFrame))` | `ret, (last, count, df) = ctx.api(...)` | get_option_screen |
| `(RET_OK, (last_page, all_count, data_list))` | `ret, (last, count, data_list) = ctx.api(...)` | get_stock_screen |

### Common Error Handling

```python
def safe_call(ctx, label, func, *args, **kwargs):
    """Call an API method safely, logging errors without crashing."""
    try:
        result = func(*args, **kwargs)
        ret = result[0]
        if ret != ft.RET_OK:
            logger.warning("%s: ret=%d msg=%s", label, ret, result[1] if len(result) > 1 else "?")
            return None
        return result
    except Exception as e:
        logger.error("%s exception: %s", label, e)
        return None
```

### Pagination Helper (APIs with next_key)

```python
def fetch_all(ctx, api_func, code, max_pages=5):
    """Paginate through an API that returns (ret, df) with df.attrs['next_key']."""
    all_data = []
    next_key = None
    for page in range(max_pages):
        result = safe_call(ctx, api_func.__name__, api_func, code, next_key=next_key)
        if result is None:
            break
        ret, df = result[0], result[1]
        if df is not None and not df.empty:
            all_data.append(df)
        next_key = df.attrs.get("next_key") if hasattr(df, "attrs") else None
        if not next_key:
            break
    return pd.concat(all_data, ignore_index=True) if all_data else None
```

### SIMULATE Enforcement (trade examples)

```python
assert trd_ctx is not None, "This example requires a trade context"
```

### Documentation (each example README.md)

- What it demonstrates (3 bullet points)
- SDK APIs used (table)
- How to run (1 command)
- Expected output (2-3 sample lines)
- Risk level

---

## 107 — Earnings Surprise Dashboard

**Directory:** `examples/107_earnings_surprise/`

### Objective

Fetch financial statements for a stock, compare actual EPS against analyst
consensus, show historical earnings price reactions, and compute a composite
"surprise score." Single-stock report card.

### SDK APIs Used

| API | Return Type | Purpose |
|-----|-------------|---------|
| `get_financials_statements()` | `(ret, dict)` | Actual EPS, revenue |
| `get_research_analyst_consensus()` | `(ret, dict)` | Consensus EPS estimates |
| `get_financials_earnings_price_move()` | `(ret, DataFrame)` | Post-earnings price reaction |
| `get_financials_earnings_price_history()` | `(ret, DataFrame)` | Pre-earnings volatility + IV crush |

### Data Flow

```
1. User provides stock code (default: US.NVDA)
2. get_financials_statements(code, 0, 0) → dict with income_statement list
   → Extract: fiscal_year, net_profit, revenue, eps (basic + diluted)
3. get_research_analyst_consensus(code) → dict with analyst_consensus list
   → Extract: current_eps_estimate, current_target_price
4. get_financials_earnings_price_move(code) → DataFrame
   → Extract: price change at T=0, T+1, T+5 (before vs after earnings)
5. get_financials_earnings_price_history(code) → DataFrame
   → Extract: predict_vola_ratio, option_iv_crush, volume
6. Compute surprise_score:
   surprise_bps = (actual_eps - consensus_eps) / |consensus_eps| * 10000
   price_reaction_bps = max(|move_0|, |move_1|)
   volatility_impact = iv_crush_pct
   → Composite: weighted (40% surprise, 30% reaction, 30% vol impact)
7. Print dashboard:
   === EARNINGS SURPRISE DASHBOARD: US.NVDA ===
   Period         | Actual EPS | Consensus | Surprise bps | Price Move T+1 | IV Crush
   2025-Q4        | $1.25      | $1.10     | +1364        | +3.2%          | -18.5%
   2025-Q3        | $0.95      | $1.02     | -686         | -2.1%          | -12.3%

   COMPOSITE SURPRISE SCORE: 73/100 (Strong Beat)
```

### Edge Cases

- No analyst consensus for this stock (may be too small) → skip surprise calc
- Financial statements not available (new IPO) → print historical price reactions only
- EPS = 0 causing division by zero → use absolute change instead of bps
- No earnings price history (never had earnings) → skip that section
- Multiple fiscal periods → show last 4 quarters, oldest first

### Acceptance Criteria

```
Given: code = "US.NVDA"
When:  script runs
Then:  prints a table with ≥1 row of earnings data
Then:  each row shows: period, actual EPS, consensus (or "N/A"), surprise bps
Then:  price move and IV crush columns are populated
Then:  composite surprise score is printed at the bottom
Then:  handles stocks with no consensus data without crashing
```

### Files

```
examples/107_earnings_surprise/
├── main.py           # entry point, dashboard logic
└── README.md
```

### Risk

None — read-only.

---

## 108 — Short Squeeze Risk Scanner

**Directory:** `examples/108_short_squeeze/`

### Objective

Scan a list of US stocks and rank them by short squeeze risk using three
metrics: short interest ratio (SI%), short volume ratio, and broker
concentration changes. Highlights stocks with rising squeeze pressure.

### SDK APIs Used

| API | Return Type | Purpose |
|-----|-------------|---------|
| `get_short_interest()` | `(ret, us_df, hk_df)` | SI%, days to cover |
| `get_daily_short_volume()` | `(ret, us_df, hk_df)` | Daily short volume ratio |
| `get_top_ten_buy_sell_brokers()` | `(ret, DataFrame)` | Broker net flow |

### Data Flow

```
1. Scan list (configurable — default: GME, AMC, NVDA, TSLA, AAPL, PLTR, SNAP)
2. For each stock:
   a. get_short_interest(code) → us_df
      - shares_short, short_percent (SI%), days_to_cover, avg_daily_share_volume
   b. get_daily_short_volume(code) → us_df
      - total_shares_short, short_percent (short vol %), volume
   c. get_top_ten_buy_sell_brokers(code, days_before=5) → DataFrame
      - net_vol, broker_name, buy_sell_type
      → compute: top_broker_concentration = top 3 net_vol / total net_vol
3. Compute squeeze_score (0–100):
   - SI% > 20% → 40 pts  | SI% > 40% → 60 pts
   - days_to_cover > 5 → 15 pts | > 10 → 25 pts
   - short_vol_ratio > 30% → 15 pts | > 50% → 25 pts
   - broker_concentration rising → 15 pts
4. Sort by squeeze_score descending
5. Print table:
   === SHORT SQUEEZE RISK SCANNER ===
   Rank | Stock | SI%    | Days2Cover | ShortVol% | BrokerConc | Score | Signal
   1    | GME   | 42.1%  | 12.3       | 55.2%     | 0.68        | 89    | 🔴 HIGH
   2    | AMC   | 28.5%  | 8.1        | 38.7%     | 0.55        | 62    | 🟡 WATCH
```

### Edge Cases

- Not a US stock → skip (short interest APIs return US-only data)
- No short data for this stock → print "No short data available"
- Broker data unavailable (needs LV1) → skip broker concentration, reduce max score
- Zero volume day → skip that stock, log warning
- Pagination: get_short_interest and get_daily_short_volume may return many rows → use latest

### Acceptance Criteria

```
Given: stock list = ["US.GME", "US.AMC", "US.NVDA"]
When:  script runs
Then:  prints a sorted rank table with ≥2 rows
Then:  each row shows: stock, SI%, days to cover, short vol %, score
Then:  scores are 0–100 scale
Then:  handles stocks with incomplete data gracefully
Then:  total runtime < 30s for 7 stocks
```

### Files

```
examples/108_short_squeeze/
├── main.py
└── README.md
```

### Risk

None — read-only.

---

## 109 — Insider Activity Monitor

**Directory:** `examples/109_insider_monitor/`

### Objective

Detect unusual insider trading patterns for a stock. Cross-reference insider
trade history with current holdings, flag cluster trades and abnormal
sale/purchase ratios.

### SDK APIs Used

| API | Return Type | Purpose |
|-----|-------------|---------|
| `get_insider_holder_list()` | `(ret, DataFrame)` | Current insider positions |
| `get_insider_trade_list()` | `(ret, DataFrame)` | Historical insider trades |
| `get_shareholders_holding_changes()` | `(ret, DataFrame)` | Broader shareholder changes |
| `get_company_executives()` | `(ret, DataFrame)` | Executive roster for context |

### Data Flow

```
1. User provides stock code (default: US.AAPL)
2. get_company_executives(code) → DataFrame
   → Cache: leader_name, position_name for later lookup
3. get_insider_holder_list(code) → DataFrame
   → Extract: holder_id, name, title, holder_quantity, holder_pct,
     insider_bought_count, insider_sold_count
4. get_insider_trade_list(code) → DataFrame
   → For each insider: recent trades (trade_shares, min_trade_date, max_trade_date,
     min_price, max_price, transaction_type)
   → Group by holder_id: total_bought, total_sold, net_change
5. get_shareholders_holding_changes(code) → DataFrame
   → Larger picture: period_text, share_change_num, share_ratio_change, holder_type
6. Compute anomaly signals:
   a. Cluster buy: ≥3 insiders bought in same week → "BUY CLUSTER"
   b. Unusual sale: insider sold >50% of holdings → "HEAVY SALE"
   c. Insider vs executive: insider selling while executive roster unchanged → neutral
   d. Net insider ratio: (bought_count - sold_count) / total_insiders
      > 0.3 → "BULLISH" | < -0.3 → "BEARISH"
7. Print report:
   === INSIDER ACTIVITY MONITOR: US.AAPL ===
   Total Insiders: 12  |  Bought (30d): 3  |  Sold (30d): 1  |  Net Ratio: +0.17

   Name              | Title         | Holdings | Bought | Sold | Net   | Signal
   Tim Cook          | CEO           | 3,200    | 0      | 0    | 0     | —
   Luca Maestri      | CFO           | 850      | 200    | 0    | +200  | BUY
   ...

   🔴 ALERT: Cluster buy detected (3 insiders, 2026-05-20 week)
   🟡 ALERT: Executive sale — Kate Adams sold 100% of holdings
```

### Edge Cases

- No insider data (non-US stock) → print "Insider data only available for US stocks"
- Insider list empty → exit with message
- Trade list empty for some insiders → show holdings only
- Division by zero when computing ratios → handle with if-else
- Pagination: insider_trade_list may have next_key → fetch up to 3 pages

### Acceptance Criteria

```
Given: code = "US.AAPL"
When:  script runs
Then:  prints insider count, bought/sold counts, net ratio
Then:  lists individual insiders with holdings and recent trade activity
Then:  flags any cluster buys or heavy sales as ALERTS
Then:  handles stocks with no insider data gracefully
```

### Files

```
examples/109_insider_monitor/
├── main.py
└── README.md
```

### Risk

None — read-only.

---

## 110 — Dividend Capture Calendar

**Directory:** `examples/110_dividend_calendar/`

### Objective

Build a forward-looking calendar of corporate action events (dividend ex-dates,
stock splits, buyback windows) for a portfolio of stocks. Computes expected
yield and suggests optimal entry/exit for dividend capture.

### SDK APIs Used

| API | Return Type | Purpose |
|-----|-------------|---------|
| `get_corporate_actions_dividends()` | `(ret, dict)` | Dividend history + schedule |
| `get_corporate_actions_buybacks()` | `(ret, dict)` | Buyback history + schedule |
| `get_corporate_actions_stock_splits()` | `(ret, dict)` | Split history |

### Data Flow

```
1. Portfolio list (configurable, default: HK.00005, HK.00002, HK.00066, HK.00001)
2. For each stock:
   a. get_corporate_actions_dividends(code) → dict
      → Parse: ex_date, cash_dividend, dividend_currency, payment_date, record_date
      → Only keep rows where ex_date >= today AND cash_dividend > 0
   b. get_corporate_actions_buybacks(code) → dict
      → Extract: hk_buy_back_list DataFrame (publ_date, end_date, buy_back_money,
        buy_back_sum, percentage, high_price, low_price)
      → Flag: active buyback = end_date >= today
   c. get_corporate_actions_stock_splits(code) → dict
      → Extract: split_list for reference (usually historical)
3. Merge into timeline sorted by ex_date:
   === DIVIDEND CAPTURE CALENDAR ===
   Date       | Stock    | Event          | Amount   | Yield% | Notes
   2026-06-05 | HK.00005 | EX-DIVIDEND    | HKD 0.90 | 3.8%   | Record: 06-06
   2026-06-12 | HK.00002 | EX-DIVIDEND    | HKD 0.65 | 4.2%   | Record: 06-13
   2026-06-15 | HK.00066 | BUYBACK ACTIVE | —        | —      | Window: -06-30
   2026-07-10 | HK.00005 | SPLIT          | 1:5      | —      | Consolidation

   STRATEGY: Buy HK.00005 on 06-03 (T-2), sell on 06-08 (T+1)
   Expected capture: HKD 0.90 per share (net of ~0.1% price drop)
```

### Edge Cases

- No upcoming dividends → show "No upcoming dividend events"
- Buyback already ended → filter out, show only active windows
- Stock split in the past → skip, only show future splits
- Dividend amount = 0 → skip zero-value events
- Dividend yield computation: annual_dividend / current_price → requires fetching price

### Acceptance Criteria

```
Given: portfolio = ["HK.00005", "HK.00002"]
When:  script runs
Then:  prints a calendar sorted by date with dividend ex-dates
Then:  shows yield % for each dividend event
Then:  marks active buyback windows
Then:  suggests optimal entry/exit dates
Then:  handles stocks with no upcoming events without crashing
```

### Files

```
examples/110_dividend_calendar/
├── main.py
└── README.md
```

### Risk

None — read-only. Price data for yield computation uses get_stock_quote().

---

## 111 — Company Health Score

**Directory:** `examples/111_company_health/`

### Objective

Compute a composite health score for a company by evaluating four dimensions:
management quality (executive profile), operational efficiency, financial
statements, and company profile. Output a radar chart (ASCII or text) and
detailed breakdown.

### SDK APIs Used

| API | Return Type | Purpose |
|-----|-------------|---------|
| `get_company_profile()` | `(ret, DataFrame)` | Industry, employees, description |
| `get_company_executives()` | `(ret, DataFrame)` | Executive roster, tenure |
| `get_company_operational_efficiency()` | `(ret, dict)` | ROE, ROA, margins |
| `get_financials_statements()` | `(ret, dict)` | Revenue, profit, debt |

### Scoring Dimensions

```
Dimension 1 — Management Quality (0–25 pts):
  - CEO tenure > 5 years: +5
  - CFO present: +5
  - Board size 5–12: +5
  - Average executive age 45–60: +5
  - No recent insider selling cluster: +5

Dimension 2 — Operational Efficiency (0–25 pts):
  - ROE > 15%: +10  | ROE > 8%: +5  | else: 0
  - Operating margin > 20%: +10  | > 10%: +5
  - Revenue per employee > industry median proxy: +5

Dimension 3 — Financial Health (0–25 pts):
  - Revenue growth YoY > 10%: +8  | > 5%: +4
  - Net profit margin > 15%: +8  | > 5%: +4
  - Debt/equity < 0.5: +9  | < 1.0: +5

Dimension 4 — Company Profile (0–25 pts):
  - Employee count > 10,000: +5 (large, established)
  - Business description mentions growing keywords: +10 (AI, cloud, biotech, etc.)
  - Industry in favored sector list: +10
```

### Data Flow

```
1. User provides stock code (default: US.NVDA)
2. get_company_profile(code) → DataFrame
   → Build dict: name→value pairs (industry, employees, description, etc.)
3. get_company_executives(code) → DataFrame
   → Compute: exec_count, avg_age, avg_tenure, has_cfo, has_ceo
4. get_company_operational_efficiency(code) → dict
   → Parse: roe, operating_margin, net_margin, roa from return data
5. get_financials_statements(code, 0, 0) → dict
   → Extract latest: revenue, net_profit, total_assets, total_liabilities
6. Compute all 4 dimension scores → total (0–100)
7. Print report:
   === COMPANY HEALTH SCORE: US.NVDA ===
   Dimension               | Score | Max | Details
   Management Quality      | 20    | 25  | CEO 12yr tenure, CFO present
   Operational Efficiency  | 22    | 25  | ROE 42%, margin 48%
   Financial Health        | 18    | 25  | Revenue +18% YoY, D/E 0.3
   Company Profile         | 15    | 25  | AI sector, 30K employees
   ---------------------------------------------------
   TOTAL                   | 75    | 100 | GRADE: A-

   RADAR:
             Mgmt
             25
            /  \
     Profile     Efficiency
            \  /
             25
          Financial
```

### Edge Cases

- No operational efficiency data (non-US stock) → score 0 for that dimension
- No executives list → score 0, skip
- Financial statements not available → use what's available, reduce max score
- description not found in profile → skip keyword matching
- Division by zero in ratios → handle with try/except

### Acceptance Criteria

```
Given: code = "US.NVDA"
When:  script runs
Then:  prints all 4 dimension scores with details
Then:  prints total score and letter grade (A/B/C/D/F)
Then:  ASCII radar chart is printed
Then:  handles missing data gracefully (partial scores)
```

### Files

```
examples/111_company_health/
├── main.py           # scoring engine + report
├── scoring.py        # dimension scoring functions
└── README.md
```

### Risk

None — read-only.

---

## 112 — Option Flow Screener

**Directory:** `examples/112_option_flow/`

### Objective

Screen the entire US options market for unusual flow using implied volatility,
exercise probability, and option screening data. Identifies options with
compressed IV/HV spreads and high probability of exercise.

### SDK APIs Used

| API | Return Type | Purpose |
|-----|-------------|---------|
| `get_option_volatility()` | `(ret, DataFrame)` | IV, HV, volatility premium |
| `get_option_exercise_probability()` | `(ret, DataFrame)` | Strike probability |
| `get_option_screen()` | `(ret, (bool, int, DataFrame))` | Screen options by criteria |

### Data Flow

```
1. Define screen criteria:
   - Markets: US (OptMarketCategory.US)
   - Filter: volume > 100, OI > 500
   - Filter: IV_HV_ratio between 0.8–1.2 (compressed vol)
   - Filter: delta 0.2–0.8 (not too deep ITM/OTM)
   - Sort by: implied_volatility  ASC (find cheapest vol)

2. OptionScreenRequest builder:
   req = OptionScreenRequest([ft.OptMarketCategory.US])
   req.add_option_filter(ft.OptionFilterType.OPTION_TYPE, ["CALL", "PUT"])
   req.add_option_filter(ft.OptionFilterType.VOLUME, lower=100)
   req.add_option_filter(ft.OptionFilterType.OPEN_INTEREST, lower=500)
   req.add_option_filter(ft.OptionFilterType.IMPLIED_VOLATILITY, lower=0.1, upper=1.0)
   req.add_option_filter(ft.OptionFilterType.DELTA, lower=0.2, upper=0.8)
   req.add_sort(ft.OptionSortType.IMPLIED_VOLATILITY, desc=False)
   req.add_option_retrieve(ft.OptionRetrieveType.IMPLIED_VOLATILITY)
   req.add_option_retrieve(ft.OptionRetrieveType.HISTORY_VOLATILITY)
   req.add_option_retrieve(ft.OptionRetrieveType.DELTA)
   req.add_option_retrieve(ft.OptionRetrieveType.OPEN_INTEREST)
   req.add_option_retrieve(ft.OptionRetrieveType.PREMIUM)
   req.add_underlying_retrieve(ft.UnderlyingRetrieveType.STOCK_PRICE)
   req.add_underlying_retrieve(ft.UnderlyingRetrieveType.STOCK_NAME)

3. get_option_screen(req) → (last_page, all_count, DataFrame)
   → Print top 20 rows

4. For top 5 results, drill down:
   a. get_option_volatility(option_code) → DataFrame
      → Latest IV, HV, volatility_premium
   b. get_option_exercise_probability(option_code) → DataFrame
      → strike_probability for each strike

5. Compute flow_score for each option:
   - IV/HV near 1.0 (compressed): +30 pts
   - Exercise probability > 40%: +30 pts (ITM exercise likely)
   - Volume/OI ratio > 0.5 (active flow): +20 pts
   - Premium < $2.00 (cheap entry): +20 pts

6. Print report:
   === OPTION FLOW SCREENER ===
   # | Underlying | Strike | Type | Expiry | IV    | HV    | IV/HV | ExProb | Vol/OI | Score
   1 | NVDA       | 120   | CALL | 06-20  | 32.5% | 35.1% | 0.93  | 52%    | 1.2    | 85
   2 | AAPL       | 200   | PUT  | 06-20  | 28.1% | 30.2% | 0.93  | 38%    | 0.8    | 72

   DRILLDOWN: NVDA 120 CALL 06-20
   IV History: 45d avg=34.2%, current=32.5% → vol compressing
   ExProb: 52% → high probability of ITM at expiry
   Recommendation: LONG CALL (premium rich in compressed vol)
```

### Edge Cases

- Option screen returns 0 results → expand criteria, print "No matching options"
- LV2 options subscription required → if empty, print "LV2 options data required"
- Drilldown API fails for a specific option → skip that one, continue
- ALL_COUNT > 200 → only first page processed (configurable)
- Option volatility API requires specific permissions → handle gracefully

### Acceptance Criteria

```
Given: script runs
When:  screen is executed
Then:  prints top 20 options sorted by IV (lowest first)
Then:  at least 3 drilldown rows with IV/HV and exercise probability
Then:  flow scores computed and shown for drilldown results
Then:  handles empty results gracefully
```

### Files

```
examples/112_option_flow/
├── main.py
├── screen_builder.py  # OptionScreenRequest construction
└── README.md
```

### Risk

None — read-only.

---

## 113 — Institutional Flow Tracker

**Directory:** `examples/113_institutional_flow/`

### Objective

Track institutional investor activity for a stock: who holds, how much they
bought/sold, and cross-reference with broker-level flow data to detect
accumulation or distribution patterns.

### SDK APIs Used

| API | Return Type | Purpose |
|-----|-------------|---------|
| `get_shareholders_institutional()` | `(ret, DataFrame)` | Aggregate institutional holdings |
| `get_shareholders_holder_detail()` | `(ret, DataFrame)` | Per-institution detail |
| `get_shareholders_holding_changes()` | `(ret, DataFrame)` | Recent changes |
| `get_top_ten_buy_sell_brokers()` | `(ret, DataFrame)` | Top broker net flow |

### Data Flow

```
1. User provides stock code (default: US.AAPL)
2. get_shareholders_institutional(code) → DataFrame
   → Extract latest: institution_quantity, holder_quantity, holder_pct,
     holder_quantity_change, holder_pct_change
3. get_shareholders_holder_detail(code) → DataFrame
   → Extract: holder_name, share_num, share_ratio, change_in_shares
   → Sort by share_ratio descending → top 10 holders
4. get_shareholders_holding_changes(code) → DataFrame
   → Filter: holder_type = INSTITUTIONAL
   → Group by: name, sum(share_change_num), max(holding_date)
   → Identify: top 5 accumulators (+), top 5 distributors (-)
5. get_top_ten_buy_sell_brokers(code, days_before=5) → DataFrame
   → net_vol, broker_name → which brokers driving the flow
6. Cross-reference:
   - If institutional holdings rising AND top brokers buying → "STRONG ACCUMULATION"
   - If institutional holdings falling AND top brokers selling → "STRONG DISTRIBUTION"
   - If institutional rising but retail selling → "INSTITUTIONAL CONVICTION"
   - Mixed signals → "MIXED — NO CLEAR DIRECTION"
7. Print report:
   === INSTITUTIONAL FLOW TRACKER: US.AAPL ===
   Period | Inst. Qty | Qty Change | Holders | Holders Change | Pct
   2026Q1 | 4,520,000 | +230,000   | 1,250   | +45            | 62.3%

   TOP 10 INSTITUTIONAL HOLDERS
   Rank | Institution          | Shares    | %Out      | Change
   1    | Vanguard Group       | 520,000   | 7.2%      | +15,000
   2    | BlackRock            | 480,000   | 6.6%      | -2,000
   3    | State Street         | 380,000   | 5.2%      | +8,000

   TOP 5 ACCUMULATORS (last period)
   + Vanguard Group: +15,000
   + Fidelity: +12,000

   TOP 5 DISTRIBUTORS
   - Berkshire Hathaway: -25,000

   BROKER FLOW (5d)
   Broker         | Net Vol | Signal
   Morgan Stanley | +45,000 | BUYING
   Goldman Sachs  | -22,000 | SELLING

   VERDICT: STRONG ACCUMULATION (institutions + brokers aligned)
```

### Edge Cases

- No institutional data (HK stock, small cap) → print "Institutional data limited"
- holder_detail not available → skip that section, continue
- broker data not available (LV1) → base verdict on institutional data only
- holder_detail returns empty DataFrame → show institutional aggregate only
- Institutional data may have next_key pagination → fetch up to 3 pages

### Acceptance Criteria

```
Given: code = "US.AAPL"
When:  script runs
Then:  prints aggregate institutional holdings for latest period
Then:  prints top 10 holders sorted by share count
Then:  prints top 5 accumulators and top 5 distributors
Then:  prints broker flow (or "N/A" if LV1 unavailable)
Then:  prints verdict: one of 4 possible signals
Then:  handles non-US stocks without crashing
```

### Files

```
examples/113_institutional_flow/
├── main.py
└── README.md
```

### Risk

None — read-only.

---

## 114 — Valuation Heat Map

**Directory:** `examples/114_valuation_heatmap/`

### Objective

Screen a market (HK or US) for valuation outliers using PE/PB/PS percentiles.
Group by industry/sector, compute median valuation percentile, and print a
color-coded heatmap of cheap vs expensive sectors.

### SDK APIs Used

| API | Return Type | Purpose |
|-----|-------------|---------|
| `get_valuation_detail()` | `(ret, dict)` | PE, PB, PS, PCF percentiles |
| `get_valuation_plate_stock_list()` | `(ret, DataFrame)` | Stocks in a plate with valuation |
| `get_stock_screen()` | `(ret, (bool, int, list))` | Screen by valuation criteria |

### Data Flow

```
1. User provides market (default: HK) and reference stock (default: HK.00700)

2. Phase 1 — Plate-level scan:
   a. get_valuation_plate_stock_list(code) → DataFrame
      → For each stock in same plate: PE, PB, PS, market_cap
   b. Group by stock → compute percentile rank within plate:
      PE_percentile = rank(stock_pe) / count(plate_stocks) * 100
      PB_percentile = rank(stock_pb) / count(plate_stocks) * 100
      Average percentile = (PE_pctile + PB_pctile + PS_pctile) / 3

3. Phase 2 — Market-wide screen:
   a. StockScreenRequest builder:
      req = StockScreenRequest()
      req.add_simple_field(ft.SimpleFilterField.MARKET, [market])
      req.add_simple_field(ft.SimpleFilterField.SECURITY_TYPE, ["STOCK"])
      req.add_retrieve_simple(ft.RetrieveSimpleField.PE)
      req.add_retrieve_simple(ft.RetrieveSimpleField.PB)
      req.add_retrieve_simple(ft.RetrieveSimpleField.MARKET_CAP)
      req.add_retrieve_simple(ft.RetrieveSimpleField.STOCK_NAME)
      req.add_retrieve_simple(ft.RetrieveSimpleField.INDUSTRY)
      req.set_sort(ft.SortDirection.DESC, ft.SortPropertyType.SIMPLE,
                   [str(ft.RetrieveSimpleField.MARKET_CAP.value)])
   b. get_stock_screen(req) → (last_page, all_count, data_list)
      → Parse data_list: each item has stock_id + results list
      → Build pandas DataFrame: stock_name, industry, PE, PB, market_cap

4. Phase 3 — Compute heat map:
   a. Group by industry → median PE, median PB, median market_cap
   b. Compute industry score:
      relative_value = industry_median_PE / market_median_PE
      if relative_value < 0.8 → "CHEAP" (green)
      if 0.8–1.2 → "FAIR" (white)
      if > 1.2 → "EXPENSIVE" (red)

5. Print report:
   === VALUATION HEAT MAP: HK ===
   Reference: HK.00700 → PE=22.5 PB=5.2 (Market avg PE=15.3)

   Sector               | Median PE | Median PB | vs Market | Signal
   Technology           | 28.5      | 6.2       | 1.86x     | 🔴 EXPENSIVE
   Financials           | 12.3      | 1.1       | 0.80x     | 🟢 CHEAP
   Real Estate          | 10.1      | 0.8       | 0.66x     | 🟢 CHEAP
   Healthcare           | 18.5      | 3.0       | 1.21x     | 🔴 EXPENSIVE
   Consumer Goods       | 15.2      | 2.5       | 0.99x     | ⚪ FAIR

   TOP 5 CHEAPEST STOCKS (by PE percentile):
   Rank | Stock       | PE   | PB   | Market Cap | Industry
   1    | HK.00001    | 5.2  | 0.6  | 185B       | Real Estate
   2    | HK.00005    | 6.8  | 0.9  | 220B       | Financials

   TOP 5 MOST EXPENSIVE STOCKS:
   Rank | Stock       | PE   | PB   | Market Cap | Industry
   1    | HK.00700    | 28.5 | 6.2  | 3,800B     | Technology
```

### Edge Cases

- No valuation data for some stocks (PE=0 or negative) → filter out, log count
- Screen results > 200 → first page only (configurable page_count)
- Industry grouping yields empty groups → skip, continue
- Reference stock not in plate → print "No plate data for reference stock"
- Market median PE = 0 (all stocks negative earnings) → use PB as primary

### Acceptance Criteria

```
Given: market = "HK", reference = "HK.00700"
When:  script runs
Then:  prints sector heat map with ≥3 sectors
Then:  each sector shows median PE, PB, vs market ratio
Then:  signal column shows CHEAP/FAIR/EXPENSIVE
Then:  top 5 cheapest AND most expensive stocks listed
Then:  total runtime < 60s
```

### Files

```
examples/114_valuation_heatmap/
├── main.py
├── screen_builder.py  # StockScreenRequest construction
└── README.md
```

### Risk

None — read-only.

---

## Implementation Order

| Order | # | Name | Est. Effort | Complexity | Dependencies |
|-------|---|------|-------------|------------|-------------|
| 1 | 110 | Dividend Capture Calendar | 1 session | Low | pandas |
| 2 | 108 | Short Squeeze Risk Scanner | 1 session | Low | pandas |
| 3 | 107 | Earnings Surprise Dashboard | 1 session | Medium | pandas, dict parsing |
| 4 | 109 | Insider Activity Monitor | 1–2 sessions | Medium | pandas, pagination |
| 5 | 113 | Institutional Flow Tracker | 1–2 sessions | Medium | pandas, pagination |
| 6 | 114 | Valuation Heat Map | 2 sessions | High | StockScreenRequest, pandas |
| 7 | 112 | Option Flow Screener | 2 sessions | High | OptionScreenRequest, pandas |
| 8 | 111 | Company Health Score | 2 sessions | High | multi-source aggregation |

**Rationale:** Calendar and Short Squeeze are straightforward data fetch +
compute. Earnings and Insider add dict parsing and pagination. Valuation and
Option require protobuf request builders (complex API). Health Score is the
most complex — aggregates 4 different return types into a composite score.

---

## Cross-Cutting Concerns

### Dict Parsing Pattern (APIs returning raw dict)

```python
def extract_field(data: dict, path: list[str], default=None):
    """Safely traverse nested dict, e.g. extract_field(d, ["income_statement", 0, "eps"])"""
    current = data
    for key in path:
        if isinstance(current, dict):
            current = current.get(key, default)
        elif isinstance(current, (list, tuple)) and isinstance(key, int):
            current = current[key] if key < len(current) else default
        else:
            return default
    return current
```

### DataFrame Safety (APIs returning 3-tuples)

```python
def unpack_short_interest(result):
    """Unpack get_short_interest 3-tuple safely."""
    if result is None:
        return None
    ret, us_df, hk_df = result
    if ret != ft.RET_OK:
        return None
    return us_df if us_df is not None and not us_df.empty else None
```

### OptionScreenRequest Builder Pattern

```python
def build_option_screen_request():
    from futu import OptionScreenRequest, OptMarketCategory
    from futu import OptionFilterType, OptionSortType, OptionRetrieveType, UnderlyingRetrieveType
    req = OptionScreenRequest([OptMarketCategory.US])
    req.add_option_filter(OptionFilterType.VOLUME, lower=100)
    req.add_option_filter(OptionFilterType.OPEN_INTEREST, lower=500)
    req.add_option_filter(OptionFilterType.IMPLIED_VOLATILITY, lower=0.1, upper=1.0)
    req.add_sort(OptionSortType.IMPLIED_VOLATILITY, desc=False)
    req.add_option_retrieve(OptionRetrieveType.IMPLIED_VOLATILITY)
    req.add_option_retrieve(OptionRetrieveType.HISTORY_VOLATILITY)
    req.add_option_retrieve(OptionRetrieveType.DELTA)
    req.add_underlying_retrieve(UnderlyingRetrieveType.STOCK_NAME)
    return req
```

### StockScreenRequest Builder Pattern

```python
def build_valuation_screen_request(market):
    from futu import StockScreenRequest, SimpleFilterField, SecurityType
    from futu import RetrieveSimpleField, SortDirection, SortPropertyType
    req = StockScreenRequest()
    req.add_simple_field(SimpleFilterField.MARKET, [market])
    req.add_simple_field(SimpleFilterField.SECURITY_TYPE, [SecurityType.STOCK])
    req.add_retrieve_simple(RetrieveSimpleField.PE)
    req.add_retrieve_simple(RetrieveSimpleField.PB)
    req.add_retrieve_simple(RetrieveSimpleField.MARKET_CAP)
    req.add_retrieve_simple(RetrieveSimpleField.STOCK_NAME)
    req.add_retrieve_simple(RetrieveSimpleField.INDUSTRY)
    req.set_sort(SortDirection.DESC, SortPropertyType.SIMPLE,
                 [str(RetrieveSimpleField.MARKET_CAP.value)])
    return req
```

### Error Handling (all examples)

```python
try:
    ctx = create_quote_context()
    # ... example logic ...
except KeyboardInterrupt:
    logger.info("Interrupted by user")
except Exception:
    logger.exception("Unhandled error")
finally:
    ctx.close()
```

### Script Boilerplate

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context
```

### Integration with run_all.py

Each example `main.py` must:
1. Accept `--code` or `--market` CLI args (with sensible defaults)
2. Return exit code 0 on success, 1 on failure
3. Print all output to stdout (not files)
4. Complete within 120s

