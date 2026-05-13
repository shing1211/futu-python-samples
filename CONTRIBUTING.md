# Contributing to futu-python-samples

## Adding a new example

1. Create the directory: `examples/XX_name/`
2. Add `main.py` — use `connect.py` for all connections:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context   # or create_trade_context

if __name__ == "__main__":
    ctx = create_quote_context()
    # ... your code ...
    ctx.close()
```

3. Update `examples/README.md` index

## Conventions

- `sys.path.insert` goes **before** any `futu` or `connect` imports
- All contexts must be `.close()`d — use `try/finally`
- Log all fields in API responses — don't silently discard data
- Trade examples: always call `unlock_trade()` first; use SIMULATE account to avoid real orders
- Push handlers: subclass the `*HandlerBase` class from `futu`

## Return type reference

> These were verified against the live remote gateway. SDK docs may differ.

| API | Returns |
|-----|---------|
| `get_history_kl_quota()` | `(used_quota: int, remain_quota: int, detail)` — a **tuple**, not dict |
| `get_security_firm()` | plain `str` |
| `request_trading_days()` | `list` of date strings |
| `get_order_book()` | `(ret_code, dict)` where dict has keys `Bid` and `Ask` — each entry is a 4-tuple `(price, vol, count, extra_dict)` |
| `subscribe()` / `unsubscribe()` | `(ret_code, None)` — 2-tuple; unpack as `ret, _ = ctx.subscribe(...)` |
| `request_history_kline()` | `(ret_code, DataFrame, next_page_token)` — **3-tuple** |
| `get_capital_flow()` | `(ret_code, DataFrame)` with columns `capital_flow_item_time`, `in_flow`, etc. — no `period_type` param |
| `get_warrant()` | `(DataFrame, has_more: bool, total_count: int)` — tuple, not just DataFrame |
| `get_price_reminder()` | `(ret_code, list_of_dicts)` — list entries have `key` field (int64 reminder ID) |
| `set_price_reminder()` | use `ft.SetPriceReminderOp` (not `PriceReminderOp`); `key` must be int64 reminder ID |
| `get_plate_list()` DataFrame column | `plate_name` not `name` |
| `subscribe` parameter | `code_list=` not `codes=` |
| `OrderBookHandlerBase` push content | dict with `Bid`/`Ask` keys; each level is `(price, vol, count)` 3-tuple |
| `SecurityReferenceType.BULL_BEAR` | **Not available** — wrap in `try/except AttributeError` |
| `AuType.BFQ` | **Does not exist** — use `AuType.HFQ` (no adjustment) or `AuType.QFQ` (adjusted) |
| `hist[-1]` on pandas Series | Raises `KeyError` — use `hist.iloc[-1]` |
| `if df:` where `df` is DataFrame | Ambiguous truth — use `if df is not None and not df.empty:` |
| Most others | `(ret_code, DataFrame)` |

## Testing

```bash
# Test all examples (recommended — Python runner with per-example timeouts)
python3 scripts/run_all.py

# Quick smoke test (shell-based, grep for errors)
bash scripts/test_all.sh

# Run one example directly
python3 examples/07_kline/main.py
```

## Push handler examples

See `02_quote_push` and `05_quote_trade` for full handler implementations:

```python
from futu import StockQuoteHandlerBase, RET_OK, RET_ERROR

class MyHandler(StockQuoteHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, content = super().on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            return RET_ERROR, content
        logger.info("Quote: %s", content)
        return RET_OK, content

ctx = create_quote_context()
ctx.set_handler(MyHandler())
ctx.subscribe("HK.00700", SubType.QUOTE)
# ... ctx stays open, pushes arrive asynchronously ...
```
