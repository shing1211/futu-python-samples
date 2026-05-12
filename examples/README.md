# Examples

## Index

| # | Name | Description |
|---|------|-------------|
| 00 | [00_connect_ha](./00_connect_ha/) | HA gateway connection — TCP probe, per-host RSA, auto-fallback |
| 01 | [01_snapshot](./01_snapshot/) | Market snapshot — `get_market_snapshot` |
| 02 | [02_quote_push](./02_quote_push/) | Real-time quote push — `subscribe` + push handlers |
| 03 | [03_filter](./03_filter/) | Stock screener — `get_stock_filter` |
| 04 | [04_macd_strategy](./04_macd_strategy/) | MACD trading strategy — K-line subscription + signal |
| 05 | [05_quote_trade](./05_quote_trade/) | Quote + trade combined — quotes, kline, ticker, orderbook, broker, trade order/deal push |
| 06 | [06_stock_sell](./06_stock_sell/) | Smart stock sell — `simple_sell` and `smart_sell` |

## 00 — connect_ha

High-availability gateway selector with TCP health checks.

**Features:**
- Parallel TCP probe to all configured hosts (3s timeout)
- Connects to fastest reachable gateway
- Per-host `is_rsa` flag: `True` = RSA encryption, `False` = plain, `None` = auto-fallback
- SDK fallback retry if primary RSA mode fails

**Usage:**
```bash
python examples/00_connect_ha/main.py
```

## 01 — snapshot

Market snapshot data for a given stock code list.

```bash
python examples/01_snapshot/main.py
```

## 02 — quote_push

Real-time quote push using handler callbacks. Demonstrates `StockQuoteHandlerBase`, `TickerHandlerBase`, `OrderBookHandlerBase`, `BrokerHandlerBase`.

```bash
python examples/02_quote_push/main.py
```

## 03 — filter

Stock screener using financial filters (`get_stock_filter`).

```bash
python examples/03_filter/main.py
```

## 04 — macd_strategy

MACD-based trading signal on K-line data. Subscribes to real-time K-lines and computes MACD crossover signals.

```bash
python examples/04_macd_strategy/main.py
```

## 05 — quote_trade

Full quote and trade demo. Covers:
- Stock quote, K-line, Ticker, OrderBook, Broker push
- HK/US/CC Trade (with trading password)
- Trade Order and Deal push

```bash
python examples/05_quote_trade/main.py
```

## 06 — stock_sell

Smart sell helpers — `simple_sell` (fixed price) and `smart_sell` (limit order logic).

```bash
python examples/06_stock_sell/main.py
```
