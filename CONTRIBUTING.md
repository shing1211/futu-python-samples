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
- Return type notes: if an API returns `dict` not `DataFrame`, print specific keys
- Trade examples: always call `unlock_trade()` first; use SIMULATE account to avoid real orders
- Push handlers: subclass the `*HandlerBase` class from `futu`

## Return type reference

| API | Returns |
|-----|---------|
| `get_history_kl_quota()` | `dict` with `used_quota`, `remain_quota` |
| `get_security_firm()` | plain `str` |
| `request_trading_days()` | `list` of date strings |
| Most others | `(ret_code, DataFrame)` |

## Testing

```bash
# Test all examples quickly
for d in examples/*/; do
  echo "=== $d ===" && timeout 10 python3 "$d/main.py" 2>&1 | grep -E "===|error|Error|Traceback" | head -5
done
```
