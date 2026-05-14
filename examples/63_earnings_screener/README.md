# 63 — Earnings Volatility Screener

Two-phase screener: Phase 1 fetches pre-earnings option IV and compares to historical vol (IV/HV ratio). Phase 2 checks post-earnings unusual activity via `get_technical_unusual()`.

**SDK APIs used:** `get_option_chain()`, `get_option_expiration_date()`, `request_history_kline()`, `get_technical_unusual()`, `get_financial_unusual()`

**Risk:** None — read-only. Earnings dates are hardcoded (no earnings calendar API exists).

```bash
python3 examples/63_earnings_screener/main.py
```
