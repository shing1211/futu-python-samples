# Futu Python Samples

> **42 examples that actually work.** Plug in your OpenD gateway, run any script, see real market data stream back.
> No mocks, no stubs — every example talks to a live Futu OpenD instance.

[![OpenAPI Version](https://img.shields.io/badge/Futu%20OpenAPI-v5-blue)](https://openapi.futunn.com/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-green)](https://www.python.org/)

---

## TL;DR — Up in 60 Seconds

```bash
git clone https://github.com/shing1211/futu-python-samples.git
cd futu-python-samples
pip install futu-api python-dotenv
cp .env.example .env        # ← edit with your gateway host

# pick any example — they're all self-contained
python3 examples/07_kline/main.py
```

That's it. No API keys, no compile step, no boilerplate to write first.

---

## What You're Getting

**Real market data, real fast.** Every example fires actual API calls against your OpenD gateway and logs the full response — every field, nothing hidden. By the time the script finishes, you'll have seen exactly what the data looks like.

**Smart gateway selection.** The `connect.py` module probes all your configured OpenD hosts simultaneously, measures real TCP latency, and picks the fastest one. If RSA is required for that host, it handles the handshake automatically. Both quote and trade contexts share the probe result — no redundant network calls.

**A catalog, not a tutorial.** 42 focused examples, each doing one thing well. Browse the index, find the feature you need, read the code, run it. No narrative, no chapter dependencies.

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

The `00` example runs a full HA handshake — TCP probes every host, prints connection latency, confirms the gateway is responding. If you see `Connected to ... RSA=True` in the logs, you're live.

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

**What `connect.py` does for you:**

- Probes all hosts in parallel with real TCP timing
- Picks the fastest reachable gateway
- Configures RSA encryption if the host requires it (with automatic fallback)
- Caches the probe result so trade and quote contexts both land on the same gateway
- Reads all config from `.env` — zero hardcoded values

---

## Examples Index

Browse by category or find the feature you need.

### Connectivity & Core

| # | What it does |
|---|-------------|
| [00](./examples/00_connect_ha/) | **HA gateway selection** — probes all hosts, picks fastest, retries RSA on failure. Start here to verify your setup. |
| [01](./examples/01_snapshot/) | **Market snapshot** — fetch every stock in a market (HK, US, SH, SZ) in one call |

### Real-Time Feeds (Push Handlers)

| # | What it does |
|---|-------------|
| [02](./examples/02_quote_push/) | **All quote push handlers** — quote, orderbook, ticker, broker queue, all running simultaneously |
| [05](./examples/05_quote_trade/) | **Quote + trade combined** — every push type in one script, with trade order/deal streams |
| [14](./examples/14_cur_kline/) | **Live K-line stream** — subscribe to real-time candlestick updates |
| [39](./examples/39_push_sysnotify/) | **System notifications** — login events, order fills, market alerts |
| [40](./examples/40_push_trade/) | **Trade push** — live order status and deal confirmations as they happen |

### Market Data

| # | What it does |
|---|-------------|
| [07](./examples/07_kline/) | **Historical + current K-lines** — fetch history with pagination, get today's bar live |
| [08](./examples/08_rt_ticker/) | **Tick-by-tick trades** — every trade print for a stock |
| [09](./examples/09_broker_queue/) | **Broker queue depth** — who's on the bid/ask, how deep |
| [10](./examples/10_orderbook/) | **10-level order book** — full bid/ask ladder with volume at each level |
| [16](./examples/16_stock_quote/) | **Stock quotes** — last price, volume, turnover, bid/ask for a list of stocks |
| [22](./examples/22_market_state/) | **Market state** — is the market pre-open, open, after-hours, or closed? |

### Filters & Screens

| # | What it does |
|---|-------------|
| [03](./examples/03_filter/) | **Stock screener** — filter by price, PE, market cap, turnover, and 20+ criteria |

### Sectors & Classifications

| # | What it does |
|---|-------------|
| [13](./examples/13_plate/) | **Sector/industry plates** — list all plates, get all stocks in a plate |
| [17](./examples/17_owner_plate/) | **Owner plates** — which plate does a stock belong to |
| [18](./examples/18_referencestock/) | **Reference stocks** — warrant and bull-bear chain reference data |
| [28](./examples/28_warrant/) | **Warrant data** — all warrants for an underlying, with issuer and implied volatility |

### Capital & Fundamentals

| # | What it does |
|---|-------------|
| [19](./examples/19_capital_flow/) | **Capital flow** — where money is flowing in/out, intraday and daily heatmap |
| [29](./examples/29_unusual/) | **Unusual activity** — unusual volume, price, technical and derivative signals |
| [27](./examples/27_code_change/) | **Code changes** — stock rename/split/reorganisations |
| [41](./examples/41_rehab/) | **Rehabilitation data** — ex-dividend, ex-rights, share consolidation dates |

### Trading (SIMULATE Account)

> All trade examples use the **SIMULATE** account only. No real orders are placed.

| # | What it does |
|---|-------------|
| [04](./examples/04_macd_strategy/) | **MACD strategy** — calculate MACD cross signals, place simulated orders |
| [06](./examples/06_stock_sell/) | **Place and modify orders** — sell with smart order types |
| [11](./examples/11_accinfo/) | **Account info + positions** — cash, margin, positions, P&L |
| [32](./examples/32_order_query/) | **Order lifecycle** — query, modify, cancel orders and their fills |
| [33](./examples/33_trading_info/) | **Trading limits** — max buy/sell quantity, margin ratios |
| [34](./examples/34_cancel_all/) | **Cancel all open orders** — emergency cleanup |
| [35](./examples/35_cashflow/) | **Cash flow history** — deposits, withdrawals, fees |
| [37](./examples/37_margin_ratio/) | **Margin ratios** — margin utilization for leveraged positions |
| [38](./examples/38_order_fee/) | **Order fees** — commission, platform fee, clear fees per order |

### Calendar & Reference Data

| # | What it does |
|---|-------------|
| [12](./examples/12_trading_days/) | **Trading days calendar** — which days each market is open |
| [20](./examples/20_ipo_list/) | **IPO calendar** — upcoming and recent IPOs per market |
| [21](./examples/21_future_info/) | **Futures specs** — contract size, tick size, trading hours |

### User Data & Administration

| # | What it does |
|---|-------------|
| [23](./examples/23_price_reminder/) | **Price alerts** — create, query, update, delete price reminders |
| [24](./examples/24_user_security/) | **Watchlist groups** — create and manage stock watchlists |
| [30](./examples/30_user_info/) | **User info** — account list, user profile, broker firm details |
| [31](./examples/31_misc/) | **Holding changes** — flag days, rehab data, watchlist operations |

### Quota & Utility

| # | What it does |
|---|-------------|
| [15](./examples/15_sub_list/) | **Subscription list** — which stocks and what types you're subscribed to |
| [25](./examples/25_option_chain/) | **Option chains** — all options for an underlying, grouped by expiration |
| [26](./examples/26_history_kl_quota/) | **K-line quota** — how many historical K-line API calls you've used today |
| [36](./examples/36_stock_basicinfo/) | **Stock basic info** — name, lot size, board lot, security type for a market or code list |

---

## Running the Full Suite

```bash
# The proper runner — shows PASS/FAIL for all 42 examples
python3 scripts/run_all.py

# Smoke test (just checks for exceptions)
bash scripts/test_all.sh
```

**How `run_all.py` classifies results:**

- Push examples (`02`, `05`, `39`, `40`) — 8s timeout, non-zero exit is expected
- `01_snapshot` — 400s timeout, fetches 21,000+ stocks across 4 markets
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

## License

MIT — see [LICENSE](./LICENSE).
