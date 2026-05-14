# 65 — Volatility Surface Builder

Fetches option chains across all available expirations, extracts IV per strike, and displays a moneyness × expiry matrix.

**SDK APIs used:** `get_option_expiration_date()`, `get_option_chain()`, `get_stock_quote()`

**Risk:** None — read-only. Limited to 10 expirations to protect quota.

```bash
python3 examples/65_vol_surface/main.py
```
