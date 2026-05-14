# 66 — Multi-Leg Options Order

Places a vertical call spread (BUY lower strike, SELL higher strike) on a SIMULATE account. Demonstrates simultaneous 2-leg order placement, fill monitoring, and net position reporting.

**SDK APIs used:** `place_order()`, `order_list_query()`, `cancel_all_order()`, `get_option_chain()`, `get_option_expiration_date()`

**Risk:** SIMULATE orders only. `cancel_all_order()` in `finally` cleans up unfilled legs.

```bash
python3 examples/66_multi_leg_order/main.py
```
