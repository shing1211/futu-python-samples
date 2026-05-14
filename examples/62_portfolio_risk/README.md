# 62 — Portfolio Risk Monitor

Polls positions and computes 6 live risk metrics with threshold alerts: concentration, leverage, buying power used, unrealized P&L, margin utilization, position count.

**SDK APIs used:** `position_list_query()`, `accinfo_query()`, `get_stock_quote()`, `get_margin_ratio()`

**Risk:** Read-only after initial unlock. No order placement.

```bash
python3 examples/62_portfolio_risk/main.py
```
