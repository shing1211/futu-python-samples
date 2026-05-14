# 58 — Options Greeks Dashboard

Live Black-Scholes Greeks (delta, gamma, theta, vega, rho) computed from option chain data.

**SDK APIs used:** `get_option_chain()`, `get_option_expiration_date()`, `get_stock_quote()`, `StockQuoteHandlerBase`

**Risk:** None — read-only, no orders placed.

```bash
python3 examples/58_options_greeks/main.py
```

Output: live table of strike × Greeks updating every 30s as underlying price moves.
