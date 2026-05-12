# Futu Python Samples

> **42 standalone examples** for the [Futu OpenAPI](https://openapi.futunn.com/) Python SDK (`futu-api`).
> Each script is self-contained and demonstrates one SDK feature with full response logging and proper resource cleanup.

## Features

| Feature | Detail |
|---------|--------|
| **HA Gateway Selection** | TCP-probes all configured OpenD hosts in parallel, connects to fastest reachable one |
| **Per-host RSA** | Each host can have its own RSA requirement; auto-fallback on connection failure |
| **Connection Caching** | Quote and trade contexts share the same gateway probe result — no redundant TCP probes |
| **Full Field Logging** | Every API response is logged with all its fields — no silent discarding of data |
| **Env-Var Config** | All host/credential config via environment variables — no hardcoded IPs or passwords |
| **Proper Cleanup** | All examples use `try/finally` + `ctx.close()` — no leaked connections |

## Install

```bash
pip install futu-api
```

Or with a virtual environment:

```bash
python -m venv .venv && source .venv/bin/activate
pip install futu-api
```

## Quick Start

```bash
# Run any example directly from the repo root
python3 examples/00_connect_ha/main.py

# Or use connect.py in your own scripts
python3 examples/07_kline/main.py
```

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Description | Default |
|----------|-------------|---------|
| `FUTU_OPEND_HOSTS` | HA gateway list — `host:port:is_rsa[,...]` | _(none)_ |
| `FUTU_ADDR` | Single host fallback | `127.0.0.1:11111` |
| `FUTU_RSA_KEY` | Path to RSA private key | `/etc/futu/keys/private_key.pem` |
| `FUTU_TCP_TIMEOUT` | TCP probe timeout (seconds) | `3` |
| `FUTU_TRADE_PWD` | Demo SIMULATE unlock password | `123456` |

**`FUTU_OPEND_HOSTS` format** — for multiple gateways with per-host RSA:

```bash
# Localhost (no RSA) + two remote gateways (RSA enabled)
export FUTU_OPEND_HOSTS="127.0.0.1:11111:False,192.168.1.100:11111:True,10.0.0.5:11111:True"
```

`.env` is gitignored — never commit real credentials.

## Architecture

All examples (except `00_connect_ha` which is the standalone reference implementation) import from `examples/connect.py`:

```python
from connect import create_quote_context, create_trade_context, get_demo_trade_password

# Quote context — TCP probes all hosts, picks fastest, configures RSA
quote_ctx = create_quote_context()

# Trade context — reuses the same gateway probe result (no redundant TCP probe)
trd_ctx = create_trade_context(filter_trdmarket=futu.TrdMarket.HK)

try:
    # ... use contexts ...
finally:
    quote_ctx.close()
    trd_ctx.close()
```

`connect.py` exports:

| Function | Description |
|----------|-------------|
| `create_quote_context(is_rsa=None)` | Create connected `OpenQuoteContext` with HA selection |
| `create_trade_context(is_rsa=None, **kwargs)` | Create `OpenSecTradeContext` sharing the same gateway |
| `get_demo_trade_password()` | Returns `FUTU_TRADE_PWD` (defaults to `"123456"` for SIMULATE) |
| `clear_connection_cache()` | Force re-probe on next context creation |

## Examples Index

All examples follow the pattern: run → log all response fields → clean up with `try/finally`.

| # | Name | Description | Key APIs |
|---|------|-------------|----------|
| 00 | [00_connect_ha](./examples/00_connect_ha/) | HA gateway selection — TCP probe, per-host RSA, auto-fallback | `OpenQuoteContext`, `get_global_state` |
| 01 | [01_snapshot](./examples/01_snapshot/) | Market snapshot for all stocks in a market | `get_market_snapshot` |
| 02 | [02_quote_push](./examples/02_quote_push/) | Real-time quote/orderbook/ticker/broker push via handlers | `StockQuoteHandlerBase`, `OrderBookHandlerBase`, `TickerHandlerBase`, `BrokerHandlerBase` |
| 03 | [03_filter](./examples/03_filter/) | Stock screener with SimpleFilter + FinancialFilter | `get_stock_filter`, `FilterStockData` |
| 04 | [04_macd_strategy](./examples/04_macd_strategy/) | MACD cross trading signal strategy | `request_history_kline`, `place_order`, `position_list_query` |
| 05 | [05_quote_trade](./examples/05_quote_trade/) | All push handlers — quote + trade combined | `CurKlineHandlerBase`, `RTDataHandlerBase`, `TradeOrderHandlerBase`, `TradeDealHandlerBase` |
| 06 | [06_stock_sell](./examples/06_stock_sell/) | Simple and smart sell order functions | `place_order`, `modify_order` |
| 07 | [07_kline](./examples/07_kline/) | Historical and current K-line data | `request_history_kline`, `get_cur_kline` |
| 08 | [08_rt_ticker](./examples/08_rt_ticker/) | Real-time tick-by-tick trade data | `get_rt_ticker`, `get_rt_data` |
| 09 | [09_broker_queue](./examples/09_broker_queue/) | Broker bid/ask queue depth | `get_broker_queue` |
| 10 | [10_orderbook](./examples/10_orderbook/) | 10-level order book bid/ask depth | `get_order_book` |
| 11 | [11_accinfo](./examples/11_accinfo/) | Account info and positions | `accinfo_query`, `position_list_query` |
| 12 | [12_trading_days](./examples/12_trading_days/) | Trading days calendar per market | `get_trading_days` |
| 13 | [13_plate](./examples/13_plate/) | Plate (sector/industry) listing and stock membership | `get_plate_list`, `get_plate_stock` |
| 14 | [14_cur_kline](./examples/14_cur_kline/) | Real-time K-line push via `CurKlineHandlerBase` | `subscribe`, `CurKlineHandlerBase` |
| 15 | [15_sub_list](./examples/15_sub_list/) | Query active subscriptions | `query_subscription` |
| 16 | [16_stock_quote](./examples/16_stock_quote/) | Real-time quote fields for a list of stocks | `get_stock_quote` |
| 17 | [17_owner_plate](./examples/17_owner_plate/) | Owner plate (industry归属) and its stocks | `get_owner_plate` |
| 18 | [18_referencestock](./examples/18_referencestock/) | Warrant/bull-bear reference stocks | `get_reference_stock` |
| 19 | [19_capital_flow](./examples/19_capital_flow/) | Capital flow heatmap and distribution | `get_capital_flow`, `get_capital_distribution` |
| 20 | [20_ipo_list](./examples/20_ipo_list/) | IPO calendar per market | `get_ipo_list` |
| 21 | [21_future_info](./examples/21_future_info/) | Futures contract details and specifications | `get_future_info` |
| 22 | [22_market_state](./examples/22_market_state/) | Market state (pre-market / open / after / closed) | `get_market_state` |
| 23 | [23_price_reminder](./examples/23_price_reminder/) | Price alert creation, query, and deletion | `set_price_reminder`, `get_price_reminder`, `update_price_reminder` |
| 24 | [24_user_security](./examples/24_user_security/) | Watchlist group CRUD — create, add, remove, list | `get_user_security_group`, `modify_user_security` |
| 25 | [25_option_chain](./examples/25_option_chain/) | Option chain by underlying and expiration date | `get_option_chain`, `get_option_expiration_date` |
| 26 | [26_history_kl_quota](./examples/26_history_kl_quota/) | Historical K-line quota usage and remaining quota | `get_history_kl_quota` |
| 27 | [27_code_change](./examples/27_code_change/) | Stock code change records (name changes, relisting) | `get_code_change` |
| 28 | [28_warrant](./examples/28_warrant/) | Warrant data by underlying — quotes and filters | `get_warrant`, `QuoteWarrant` |
| 29 | [29_unusual](./examples/29_unusual/) | Unusual activity alerts — technical, financial, derivative | `get_unusual`, `SkillWrapTechnicalUnusualQuery` |
| 30 | [30_user_info](./examples/30_user_info/) | Account list, user info, and broker firm details | `get_account_list`, `get_user_info` |
| 31 | [31_misc](./examples/31_misc/) | Holding changes, rehab data, watchlist groups | `get_holding_change_list`, `get_rehab`, `get_user_security_group` |
| 32 | [32_order_query](./examples/32_order_query/) | Order query, modify, cancel, and deal history | `order_list_query`, `modify_order`, `cancel_order`, `deal_list_query` |
| 33 | [33_trading_info](./examples/33_trading_info/) | Max buy/sell quantity and margin info | `acctradinginfo_query` |
| 34 | [34_cancel_all](./examples/34_cancel_all/) | Cancel all open orders in one call | `cancel_all_order` |
| 35 | [35_cashflow](./examples/35_cashflow/) | Account cash flow history | `get_history_cash_flow` |
| 36 | [36_stock_basicinfo](./examples/36_stock_basicinfo/) | Stock basic info by market or code list | `get_stock_basicinfo` |
| 37 | [37_margin_ratio](./examples/37_margin_ratio/) | Margin ratio for positions | `get_margin_ratio` |
| 38 | [38_order_fee](./examples/38_order_fee/) | Order fee query per order | `order_fee_query` |
| 39 | [39_push_sysnotify](./examples/39_push_sysnotify/) | System notification push — login, connectivity | `SysNotifyHandlerBase` |
| 40 | [40_push_trade](./examples/40_push_trade/) | Trade order and deal push — live order status | `TradeOrderHandlerBase`, `TradeDealHandlerBase` |
| 41 | [41_rehab](./examples/41_rehab/) | Rehabilitation / ex-dividend / ex-right data | `get_rehab` |

Full per-example descriptions in [examples/README.md](./examples/README.md).

## RSA Encryption (Remote OpenD)

Remote OpenD instances require RSA encryption. The SDK has **no automatic localhost-vs-remote detection** — RSA is purely client-side opt-in based on `SysConfig.IS_PROTO_ENCRYPT`.

```python
from futu import SysConfig
SysConfig.enable_proto_encrypt(True)
SysConfig.set_init_rsa_file("/path/to/private_key.pem")
ctx = OpenQuoteContext(host="remote-gateway", port=11111)
```

`connect.py` handles this automatically per-host using the `is_rsa` flag in `FUTU_OPEND_HOSTS`.

## SDK Reference

- **Docs**: https://openapi.futunn.com/futu-api-doc/
- **PyPI**: https://pypi.org/project/futu-api/
- **Version**: `futu-api 10.5.6508`

## License

MIT — see [LICENSE](./LICENSE).