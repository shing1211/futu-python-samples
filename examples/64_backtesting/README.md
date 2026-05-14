# 64 — Backtesting Mini-Framework

Pulls historical K-lines, runs a parameterized strategy, and computes performance metrics. Three built-in strategies: SMA Cross, RSI, MACD.

**SDK APIs used:** `request_history_kline()` (paginated), `get_history_kl_quota()`

**Metrics:** Total Return, Sharpe Ratio, Max Drawdown, Win Rate

**Risk:** None — read-only, no order placement.

```bash
python3 examples/64_backtesting/main.py
```
