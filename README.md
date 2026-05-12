# Futu Python Samples

> 42 standalone examples covering the [Futu OpenAPI](https://openapi.futunn.com/) Python SDK (`futu-api`).

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
# Run any example directly
python3 examples/00_connect_ha/main.py

# Or from the repo root (all examples use sys.path trick)
cd ~/github/futu-python-samples
python3 examples/07_kline/main.py
```

## Examples Index

| # | Name | Description |
|---|------|-------------|
| 00 | [00_connect_ha](./examples/00_connect_ha/) | HA gateway — TCP probe, per-host RSA, auto-fallback |
| 01 | [01_snapshot](./examples/01_snapshot/) | Market snapshot for all stocks |
| 02 | [02_quote_push](./examples/02_quote_push/) | Real-time quote/orderbook/ticker/broker push |
| 03 | [03_filter](./examples/03_filter/) | Stock screener (SimpleFilter + FinancialFilter) |
| 04 | [04_macd_strategy](./examples/04_macd_strategy/) | MACD cross trading signal |
| 05 | [05_quote_trade](./examples/05_quote_trade/) | Quote + trade push combined |
| 06 | [06_stock_sell](./examples/06_stock_sell/) | Simple and smart sell |
| 07 | [07_kline](./examples/07_kline/) | get_cur_kline + request_history_kline |
| 08 | [08_rt_ticker](./examples/08_rt_ticker/) | Real-time tick data |
| 09 | [09_broker_queue](./examples/09_broker_queue/) | Broker bid/ask queue |
| 10 | [10_orderbook](./examples/10_orderbook/) | 10-level order book depth |
| 11 | [11_accinfo](./examples/11_accinfo/) | Account info + positions |
| 12 | [12_trading_days](./examples/12_trading_days/) | Trading days calendar |
| 13 | [13_plate](./examples/13_plate/) | Plate (sector) listing |
| 14 | [14_cur_kline](./examples/14_cur_kline/) | Real-time K-line push |
| 15 | [15_sub_list](./examples/15_sub_list/) | Query subscription list |
| 16 | [16_stock_quote](./examples/16_stock_quote/) | Real-time quote fields |
| 17 | [17_owner_plate](./examples/17_owner_plate/) | Owner plate + referencestock |
| 18 | [18_referencestock](./examples/18_referencestock/) | Warrant/bull-bear reference stocks |
| 19 | [19_capital_flow](./examples/19_capital_flow/) | Capital flow + distribution |
| 20 | [20_ipo_list](./examples/20_ipo_list/) | IPO calendar |
| 21 | [21_future_info](./examples/21_future_info/) | Futures contract info |
| 22 | [22_market_state](./examples/22_market_state/) | Market state (pre/open/after/closed) |
| 23 | [23_price_reminder](./examples/23_price_reminder/) | Price alerts |
| 24 | [24_user_security](./examples/24_user_security/) | Watchlist group management |
| 25 | [25_option_chain](./examples/25_option_chain/) | Option chain + expiration dates |
| 26 | [26_history_kl_quota](./examples/26_history_kl_quota/) | K-line quota usage |
| 27 | [27_code_change](./examples/27_code_change/) | Stock code change records |
| 28 | [28_warrant](./examples/28_warrant/) | Warrant data |
| 29 | [29_unusual](./examples/29_unusual/) | Technical/financial/derivative unusual |
| 30 | [30_user_info](./examples/30_user_info/) | Account list, user info, broker |
| 31 | [31_misc](./examples/31_misc/) | Holding changes, rehab, user groups |
| 32 | [32_order_query](./examples/32_order_query/) | Order query, modify, cancel, deals |
| 33 | [33_trading_info](./examples/33_trading_info/) | Max buy/sell quantity |
| 34 | [34_cancel_all](./examples/34_cancel_all/) | Cancel all open orders |
| 35 | [35_cashflow](./examples/35_cashflow/) | Account cash flow |
| 36 | [36_stock_basicinfo](./examples/36_stock_basicinfo/) | Stock basic info |
| 37 | [37_margin_ratio](./examples/37_margin_ratio/) | Margin ratio for positions |
| 38 | [38_order_fee](./examples/38_order_fee/) | Order fee query |
| 39 | [39_push_sysnotify](./examples/39_push_sysnotify/) | System notification push |
| 40 | [40_push_trade](./examples/40_push_trade/) | Trade order/deal push |
| 41 | [41_rehab](./examples/41_rehab/) | Rehabilitation / ex-dividend data |

Full index in [examples/README.md](./examples/README.md).

## Shared Connection Module

`examples/connect.py` provides HA gateway selection — all examples import from it:

```python
from connect import create_quote_context, create_trade_context

quote_ctx = create_quote_context()   # TCP-probes all hosts, RSA auto-configured
trade_ctx = create_trade_context()    # same for trade context
```

See [00_connect_ha](./examples/00_connect_ha/) for the full HA pattern.

## RSA Encryption (Remote OpenD)

Remote OpenD instances require RSA. The SDK has **no automatic localhost-vs-remote detection** — RSA is purely client-side opt-in:

```python
from futu import SysConfig
SysConfig.enable_proto_encrypt(True)
SysConfig.set_init_rsa_file("/etc/futu/keys/private_key.pem")
ctx = OpenQuoteContext(host="172.18.208.88", port=11111)
```

`connect.py` handles this automatically per-host.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FUTU_OPEND_HOSTS` | HA gateway list (host:port:is_rsa[,...]); overrules FUTU_ADDR | _(none)_ |
| `FUTU_ADDR` | Single host fallback (host:port) | `127.0.0.1:11111` |
| `FUTU_RSA_KEY` | Path to RSA private key | `/etc/futu/keys/private_key.pem` |
| `FUTU_TCP_TIMEOUT` | TCP probe timeout (seconds) | `3` |
| `FUTU_TRADE_PWD` | Demo SIMULATE trade unlock password | `123456` |

For local development, copy `.env.example` to `.env` and fill in your values.
`.env` is gitignored — never commit real credentials.

## License

MIT — see [LICENSE](./LICENSE).
