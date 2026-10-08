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

## Connecting to OpenD

Every example reaches OpenD through `examples/connect.py`, which resolves its
configuration from the environment. Copy `.env.example` to `.env` and set at
least a host and the RSA key path.

### RSA is required whenever the gateway uses protocol encryption

FutuOpenD enables protocol encryption whenever it is started with a
protocol-encryption key — `<rsa_private_key>` in its `FutuOpenD.xml`. **That
includes a gateway on localhost.** "It's local, so it doesn't need RSA" is the
single most common cause of a connection that appears to hang.

The path in `FUTU_RSA_KEY` must match `<rsa_private_key>`:

```bash
grep rsa_private_key /opt/futu/opend/FutuOpenD.xml
```

A wrong or unreadable path does **not** fail fast. The SDK retries a failed
handshake internally and indefinitely, so the symptom is an example that hangs
until it is killed, reported as a timeout with `check sha error` and no hint
that the cause is a filesystem path. `connect.py` therefore validates the key
before any handshake and raises an error naming the path:

```
RSA private key at '/wrong/path.pem' does not exist. Set FUTU_RSA_KEY to the
path of the OpenD protocol-encryption key (<rsa_private_key> in FutuOpenD.xml).
```

### Configuring hosts

```bash
# host:port:is_rsa, comma-separated, for HA selection
FUTU_OPEND_HOSTS="127.0.0.1:11111:True"

# single host, no HA -- only consulted when FUTU_OPEND_HOSTS is unset
FUTU_ADDR=127.0.0.1:11111
```

`is_rsa` defaults to **True** in both forms when the flag is omitted, because
that is correct for nearly every gateway including local ones. Both variables
apply the same default; they used to disagree, which made the same host behave
differently depending on which one you set.

If your gateway genuinely runs without protocol encryption, state it
explicitly:

```bash
FUTU_OPEND_HOSTS="127.0.0.1:11111:False"
```

## Verification — Two Tiers

There are two independent verification tiers. They assert different things and
neither implies the other.

| | Live tier | Static tier |
|---|---|---|
| Command | `python3 scripts/run_all.py` | `python3 scripts/run_static.py` |
| Needs a gateway | **Yes** | No |
| Asserts | runtime behavior against OpenD | source properties only |
| Speed | minutes to hours | seconds |

A clean static run says **nothing** about whether an example works. Only the
live tier can establish that, because only it can reach OpenD.

### The live tier

```bash
python3 scripts/run_all.py              # every example
python3 scripts/run_all.py --only 07_kline
python3 scripts/run_all.py --list
```

It reads connection settings from your environment or `.env` and never injects
a host, key path, or password of its own. The example set is discovered from
the filesystem, so it cannot drift out of agreement with the repository.

Every example ends in exactly one of four states:

| State | Meaning | Counts as a pass? |
|---|---|---|
| `PASS` | ran to completion, exit 0 | yes |
| `FAIL` | ran and exited non-zero, or errored | no |
| `BLOCKED` | refused by external state — no gateway, no session, gateway cooldown, refused handshake | **no** |
| `NOT-VERIFIED` | discovered but not run | **no** |

A pass means the example ran and demonstrated its behavior. `BLOCKED` and
`NOT-VERIFIED` are reported separately and never inflate the pass count, so the
number is worth reading.

Verdicts are derived from **exit status**. A non-zero exit is a failure,
unconditionally. The runner inspects captured output only to *downgrade* a
failure — to `BLOCKED`, or to the expected outcome for an example designed not
to terminate — and never to turn a failure into a pass. An example that crashes
silently is a failure, not a pass.

### Declaring an example's run class

An example is time-limited by default (30s). Two classifications adjust that,
and the runner fails fast on startup if either names an example that does not
exist or if the two overlap:

- **Not terminating** (`UNBOUNDED_EXAMPLES`) — a `while True` loop that exits
  only on Ctrl-C. For these, a timeout is the expected outcome. Only genuinely
  unbounded examples belong here: declaring a bounded example unbounded turns a
  real hang into an expected outcome, which is the exact failure this runner
  exists to catch.
- **Slow** (`SLOW_EXAMPLES`) — bounded, but longer than the default. Give it a
  ceiling above its own runtime.

If your example runs for a caller-chosen window, take a `--max-minutes`
argument (see `examples/68_trailing_stop`). The runner then asks for a short
window via `DURATION_LIMITED_EXAMPLES` and the example completes and reports a
real verdict, instead of being killed at the ceiling.

### The static tier

```bash
python3 scripts/run_static.py --list
python3 scripts/run_static.py
python3 scripts/run_static.py --checks error-suppression
```

Gateway-free, standard library only. It checks a deliberately closed set of
properties decidable from source: byte-compilation, license header, the example
skeleton, error suppression, dead constants, index coverage, and contract-table
duplication. It asserts nothing about runtime behavior and cannot tell you an
example works.

Findings carry a severity. Only `fail` affects the exit status; `report`
surfaces a finding for a human to judge.

```bash
python3 scripts/run_static.py --style --style-severity=info
```

`--style` additionally runs `ruff` and `black` if they are installed. **Style is
advisory, not a gate**: `black` and `ruff` are configured in `pyproject.toml`
but have never been enforced, and this repository has no consistent formatting
baseline to enforce one against. Style findings therefore default to `info` and
never fail the tier. Pass `--style-severity=fail` to opt into gating locally.

## Reporting errors instead of swallowing them

The live tier trusts exit status, which only works if an example can actually
exit non-zero. So an example must not make its own failures invisible.

```python
# ✗ wrong — the caller cannot tell "nothing available" from "the fetch failed"
try:
    reports = fetch(code)
except Exception:
    pass

# ✓ right — record the failure, then decide
try:
    reports = fetch(code)
except Exception as exc:
    logger.error("fetch(%s) failed: %s: %s", code, type(exc).__name__, exc)
    reports = []
```

### When suppression is correct

Sometimes you genuinely want to continue past a failure — a monitor loop
surviving a transient error, an interruptible listen loop, a best-effort helper
that returns a sentinel. Narrow the handler to the case you actually handle and
record the justification inline:

```python
# Ctrl-C ends the listen loop; handled in finally
except KeyboardInterrupt:
    pass  # static-checks: allow-suppress -- Ctrl-C ends the listen loop
```

The `error-suppression` check accepts a handler only when its entire body is
`pass` or `continue`. A handler that logs, counts, or re-raises is already
observable and needs no marker. Without a marker, the check reports the site —
so a newly added suppression cannot inherit an earlier review by accident.

## Known debt

- **Contract tables are duplicated.** The return-shape, enum, and pandas tables
  in this file and in `AGENTS.md` are near-identical copies with a manual
  obligation to keep both in sync. The `contract-table-duplication` check
  reports this. The OpenSpec change `sdk-contracts-and-verification` introduces
  a single authoritative artifact that will replace both; until it is archived,
  these prose tables remain the practical source.
- **The index is incomplete.** Some baseline API-coverage examples are not yet
  listed in `examples/README.md`. The `index-coverage` check reports them.
