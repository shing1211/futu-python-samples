# Contributing to futu-python-samples

Think you found a better way to use an API? Spotted a missing example? PRs welcome.

---

## Adding a New Example

**Step 1 — Create the directory**

```bash
examples/XX_your_feature_name/
```

Use a two-digit prefix matching the current highest number + 1. The prefix controls sort order in the index.

**Step 2 — Write `main.py`**

Every example follows the same skeleton. Start from this template:

```python
import sys
from pathlib import Path

# Always add the repo root to sys.path first — before any futu or connect imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import futu as ft
from connect import create_quote_context   # or create_trade_context

if __name__ == "__main__":
    ctx = create_quote_context()

    try:
        # ... your API calls here ...
        ctx.close()
    except Exception:
        ctx.close()
        raise
```

> **Always `ctx.close()`**, even if the API call throws. Unclosed contexts leak the TCP connection to OpenD.

**Step 3 — Update the index**

Add your example to `examples/README.md` under the right section. No need to update the root `README.md` — it auto-links from `examples/README.md`.

---

## Code Conventions

These aren't stylistic preferences — they're rules that keep examples consistent and prevent the most common bugs:

### Always set up `sys.path` before imports

```python
# ✓ correct
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft

# ✗ wrong — may import a system-wide futu package instead
import futu as ft
```

### Always close your contexts

```python
# ✓ correct — guaranteed cleanup
try:
    ctx = create_quote_context()
    ret, data = ctx.get_stock_quote("HK.00700")
finally:
    ctx.close()

# ✗ wrong — leaks connection on exception
ctx = create_quote_context()
ret, data = ctx.get_stock_quote("HK.00700")
ctx.close()
```

### Log all fields — don't silently drop data

Every API call returns structured data. Log enough of it that someone running the example can verify the response looks right, even if they don't have a Bloomberg terminal open.

```python
ret, data = ctx.get_stock_quote(code_list)
if ret != 0:
    logger.error("get_stock_quote failed: %s", data)
else:
    logger.info("Quote for %s:\n%s", code_list, data.to_string())
```

### Trade examples — always use SIMULATE

Trade examples must call `unlock_trade()` before placing any orders. Always use the SIMULATE account:

```python
from connect import get_demo_trade_password

trd_ctx = create_trade_context()
trd_ctx.unlock_trade(get_demo_trade_password())
# ... place orders ...
```

### Push handlers — subclass the `*HandlerBase` class

```python
from futu import StockQuoteHandlerBase, RET_OK, RET_ERROR

class MyHandler(StockQuoteHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, content = super().on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            return RET_ERROR, content
        logger.info("Quote update: %s", content)
        return RET_OK, content

ctx = create_quote_context()
ctx.set_handler(MyHandler())
ctx.subscribe("HK.00700", ft.SubType.QUOTE)

# ctx stays open — pushes arrive asynchronously for 30s, then the loop exits
import time; time.sleep(30)
ctx.close()
```

---

## Return Type Reference

> **Heads up: the official SDK docs are sometimes outdated.** This table reflects what the live gateway actually returns. If you find a discrepancy, update this file and the corresponding AGENTS.md quirk list.

The vast majority of Futu APIs return a 2-tuple: `(ret_code, DataFrame_or_error_message)`. But there are important exceptions:

| API | Actual return | What to watch |
|-----|--------------|---------------|
| `get_history_kl_quota()` | `(used: int, remain: int, detail: None)` — **3-tuple**, not a dict | The detail field is always `None` in practice |
| `request_history_kline()` | `(ret, DataFrame, next_page_token)` — **3-tuple** | The third value is a pagination cursor, not a second DataFrame |
| `get_warrant()` | `(DataFrame, has_more: bool, total_count: int)` — **3-tuple** | `has_more` tells you if results were truncated |
| `get_order_book()` | `(ret, dict)` — dict with `Bid` and `Ask` keys | Each level is a 4-tuple: `(price, vol, count, extra_dict)` |
| `subscribe()` / `unsubscribe()` | `(ret_code, None)` — 2-tuple | Unpack it: `ret, _ = ctx.subscribe(...)` or the tuple leaks into your DataFrame code |
| `get_capital_flow()` | `(ret, DataFrame)` with columns `capital_flow_item_time`, `in_flow`, etc. | **No `period_type` parameter** — intraday vs daily depends on the market |
| `get_price_reminder()` | `(ret, list_of_dicts)` | Each dict has a `key` field — that's the int64 reminder ID |
| `set_price_reminder()` | `ret_code` only | For ADD, use `key=0`. For UPDATE/DELETE, pass the `key` from `get_price_reminder()` |
| `request_trading_days()` | `list[str]` — plain list of date strings | No `(ret, list)` tuple wrapper |

**DataFrame column names that differ from intuition:**

| API | Gotcha |
|-----|--------|
| `get_plate_list()` | The name column is `plate_name`, not `name` |
| `get_owner_plate()` | Returns a 2-tuple `(ret, DataFrame)` — `owner_board` and `plate_code` columns |
| `get_cur_kline()` | Returns a 2-tuple `(ret, DataFrame)` with 12 columns including `klines` |

**Enum names that don't exist:**

| What you might try | What actually works |
|--------------------|--------------------|
| `ft.AuType.BFQ` | `ft.AuType.HFQ` (no adjustment) or `ft.AuType.QFQ` (forward-adjusted) |
| `ft.PriceReminderOp` | `ft.SetPriceReminderOp` — `PriceReminderOp` does not exist in this SDK version |
| `ft.SecurityReferenceType.BULL_BEAR` | **Not available** — wrap in `try/except AttributeError` |

**pandas pitfalls — these will bite you:**

```python
# ✗ KeyError — hist[-1] doesn't work on a Series when index isn't integer
latest_hist = hist[-1]

# ✓ correct
latest_hist = hist.iloc[-1]

# ✗ ValueError — ambiguous truth on a DataFrame
if df: ...

# ✓ correct
if df is not None and not df.empty: ...

# ✗ — can't iterate a DataFrame row as a tuple the same way as a 4-tuple
for price, vol, count, extra in bid_levels: ...

# ✓ — DataFrame rows need .itertuples() or .iterrows()
for row in bid_levels.itertuples():
    price, vol, count = row.price, row.vol, row.count
```

---

## Testing Your Example

```bash
# Run one example in isolation
python3 examples/07_kline/main.py

# Run all 42 through the full test suite
python3 scripts/run_all.py
```

`run_all.py` checks each example for exceptions and classifies them. Push examples (`02`, `05`, `39`, `40`) are expected to time out or exit quickly — that's normal, not a failure.

If your example makes a trade API call and the gateway returns "password locked" (too many failed attempts), the runner records it as **PASS** with a "trade locked" annotation. This is a time-based gateway cooldown, not a bug in your code.
