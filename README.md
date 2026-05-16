# Futu Python Samples

> **98 examples that actually work.** Plug in your OpenD gateway, run any script, see real market data stream back.
> No mocks, no stubs — every example talks to a live Futu OpenD instance.

[![OpenAPI Version](https://img.shields.io/badge/Futu%20OpenAPI-v5-blue)](https://openapi.futunn.com/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-green)](https://www.python.org/)
[![SDK Version](https://img.shields.io/badge/SDK-10.5.6508-blue)](https://pypi.org/project/futu-api/)
[![Changelog](https://img.shields.io/badge/changelog-v1.6.0-orange)](./CHANGELOG.md)

---

## What's New in v1.6.0

- **HA health monitoring + auto-failover** — `connect.py` now runs a background daemon thread that pings the active gateway every 15s, automatically fails over to the next-best host on N consecutive failures, and fires lifecycle hooks (`on_connect`, `on_failover`, `on_disconnect`, `on_heartbeat`)
- **Retry with fallback chain** — if the fastest host fails API connect, tries every other reachable host before raising, with configurable exponential backoff
- **New example 98 (`ha_diagnostics`)** — interactive HA diagnostic tool with real-time heartbeat display, failover detection, and connection statistics
- All existing examples unchanged — 100% backward compatible

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

**A catalog, not a tutorial.** 98 focused examples, each doing one thing well. Browse the index, find the feature you need, read the code, run it.

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

## Examples (98 total)

Full categorized index → [examples/README.md](examples/README.md)

### Quick index by category

| Category | Examples |
|----------|----------|
| **Connectivity & Core** | 00, 01, 98 |
| **Market Data** | 07, 08, 09, 10, 14, 16, 22, 44 |
| **Filters & Screens** | 03, 52 |
| **Sectors, Plates & References** | 13, 17, 18, 28 |
| **Capital & Fundamentals** | 19, 27, 29, 41, 42 |
| **Advanced Analytics & Algo** | 58–67 |
| **Advanced Execution Strategies** | 68–82 |
| **Screening & Volatility** | 83–85 |
| **Market Breadth & Alerts** | 86, 87 |
| **Risk Management (SIMULATE)** | 88, 92, 96 |
| **Cross-Market & Signals** | 89, 90, 91, 95, 97 |
| **Options Strategies (SIMULATE)** | 93, 94 |
| **Real-Time Feeds (Push)** | 02, 05, 14, 39, 40, 45, 45b, 46, 47, 48 |
| **Trading (SIMULATE)** | 04, 06, 11, 32–35, 37–40, 49–51 |
| **Calendars & Reference** | 12, 20, 21, 53 |
| **User Data & Alerts** | 23, 24, 30, 31 |
| **Utilities** | 15, 25, 26, 36, 43 |

---

## Running the Full Suite

```bash
# The proper runner — shows PASS/FAIL for all 98 examples
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
│   ├── README.md           ← full 98-example index
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
│   ├── 97_vwap_anchored/   ← VWAP-based support/resistance signals
│   └── 98_ha_diagnostics/  ← HA health + failover diagnostics
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