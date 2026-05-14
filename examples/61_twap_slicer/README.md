# 61 — TWAP Order Slicer

Slices a large simulated order into N child orders over M minutes. Each slice reads `get_order_book()` to price at the best bid/ask without sweeping the spread.

**SDK APIs used:** `place_order()`, `order_list_query()`, `cancel_all_order()`, `get_order_book()`, `get_market_snapshot()`

**Risk:** SIMULATE orders only. `cancel_all_order()` in `finally` block cleans up unfinished slices.

```bash
python3 examples/61_twap_slicer/main.py
```
