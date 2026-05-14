# 60 — Cross-Market Arbitrage Spread Monitor

Tracks dual-listed stocks across HK and US markets (e.g. HK.00700 / US.TCEHY). Computes the ADR-equivalent price and logs spread in bps.

**SDK APIs used:** `StockQuoteHandlerBase`, `subscribe(QUOTE)`, `get_stock_quote()`

**Risk:** None — read-only, no orders placed.

**Pairs monitored:** Tencent, Alibaba, Baidu, JD.com

```bash
python3 examples/60_cross_market_arb/main.py
```
