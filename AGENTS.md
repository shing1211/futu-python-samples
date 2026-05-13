# futu-python-samples — AGENTS.md

## What This Project Is

42 standalone examples for the Futu OpenAPI Python SDK. Every script fires real API calls against a live OpenD gateway — no mocks, no stubs.

**Repo:** `https://github.com/shing1211/futu-python-samples`
**SDK docs:** https://openapi.futunn.com/futu-api-doc/

## Running Examples

```bash
# Single example
python3 examples/07_kline/main.py

# Full suite with PASS/FAIL report
python3 scripts/run_all.py

# Quick smoke test
bash scripts/test_all.sh
```

## Configuration

All settings live in `.env` at the repo root. The key one is `FUTU_OPEND_HOSTS`:

| Variable | What it does | Default |
|----------|-------------|---------|
| `FUTU_OPEND_HOSTS` | `host:port:is_rsa[,...]` HA list | falls back to `FUTU_ADDR` |
| `FUTU_ADDR` | Single host fallback | `127.0.0.1:11111` |
| `FUTU_RSA_KEY` | RSA private key path | `/etc/futu/keys/private_key.pem` |
| `FUTU_TCP_TIMEOUT` | TCP probe timeout | `3` seconds |
| `FUTU_TRADE_PWD` | SIMULATE unlock password | `123456` |

**Remote hosts need RSA.** The `is_rsa` flag in `FUTU_OPEND_HOSTS` is per-host — a remote gateway won't respond without it. There is no automatic localhost-vs-remote detection. The client opts in explicitly.

## ⚠️ SDK Quirks — These Will Bite You

> The official Futu SDK docs lag the live gateway. These were all verified against a real OpenD instance. If you find something new, update this list.

### Return types that differ from the docs

**`get_history_kl_quota()` — returns a plain tuple, not a dict**

```python
# ✗ wrong — docs suggest dict
quota = ctx.get_history_kl_quota()
used = quota['used_quota']

# ✓ correct — it's (used: int, remain: int, None)
used, remain, _ = ctx.get_history_kl_quota()
```

**`request_history_kline()` — 3-tuple, not 2-tuple**

```python
# ✗ wrong — assumed 2-tuple
ret, df = ctx.request_history_kline(...)

# ✓ correct — third value is the pagination cursor
ret, df, next_token = ctx.request_history_kline(...)
if next_token:
    ret, df2, next_token = ctx.request_history_kline(..., next_page_token=next_token)
```

**`get_warrant()` — also a 3-tuple with `has_more` and `total_count`**

```python
warrant_df, has_more, total = ctx.get_warrant(...)
```

**`subscribe()` and `unsubscribe()` — return `(ret_code, None)`, not just `ret_code`**

```python
# ✗ wrong — ret is actually a tuple
ret = ctx.subscribe("HK.00700", ft.SubType.QUOTE)
logger.info("subscribe ret=%d", ret)   # TypeError: %d format

# ✓ correct
ret, _ = ctx.subscribe("HK.00700", ft.SubType.QUOTE)
logger.info("subscribe ret=%d", ret)
```

**`get_order_book()` — returns a dict, not a DataFrame**

```python
# ✗ wrong — bid is a dict of lists, not a DataFrame
ret, bid = ctx.get_order_book("HK.00700")
top_bid_price = bid.iloc[-1]['price']

# ✓ correct — entries are 4-tuples (price, vol, count, extra_dict)
ret, book = ctx.get_order_book("HK.00700")
price, vol, count, _ = book['Bid'][0]
```

### Enum names that don't exist

| What the docs imply | Reality |
|---------------------|---------|
| `ft.AuType.BFQ` | **Not found** — use `ft.AuType.HFQ` (no adjustment) or `ft.AuType.QFQ` (adjusted) |
| `ft.PriceReminderOp` | **Not found** — it's `ft.SetPriceReminderOp` |
| `ft.SecurityReferenceType.BULL_BEAR` | **Not available** in this SDK version — guard with `try/except AttributeError` |

### pandas traps

```python
# ✗ KeyError — Series negative indexing doesn't work this way
hist = macd['hist']
latest = hist[-1]

# ✓ correct
latest = hist.iloc[-1]

# ✗ ValueError — DataFrame has ambiguous truth value
if df: ...

# ✓ correct
if df is not None and not df.empty: ...
```

### DataFrame column names

```python
# get_plate_list() — column is 'plate_name', not 'name'
plate_df['plate_name']   # ✓

# get_capital_flow() — no period_type parameter, columns are:
# 'capital_flow_item_time', 'in_flow', 'main_flow_in', 'main_flow_out'
```

### Parameter names

```python
# subscribe/unsubscribe take code_list=, NOT codes=
ctx.subscribe(code_list=["HK.00700"], ...)
ctx.unsubscribe(code_list=["HK.00700"], ...)

# get_capital_flow() takes NO period_type parameter
# intraday vs daily is determined by market, not a parameter
ctx.get_capital_flow("HK.00700")  # ✓
ctx.get_capital_flow("HK.00700", period_type=...)  # ✗ TypeError
```

### Push handler content shapes

```python
# OrderBookHandlerBase — content is a dict with Bid/Ask
# each level is (price, vol, count) — a 3-tuple, not a dict
def on_recv_rsp(self, rsp_pb):
    ret, content = super().on_recv_rsp(rsp_pb)
    bid_levels = content['Bid']      # list of 3-tuples
    ask_levels = content['Ask']      # list of 3-tuples
    price, vol, count = bid_levels[0]

# SysNotifyHandlerBase — content is (main_type, sub_type, msg)
main_type, sub_type, msg = content
```

## Architecture

`examples/connect.py` is the backbone. Every example (except `00`) imports from it.

**What it exports:**

| Function | What it does |
|----------|-------------|
| `create_quote_context(is_rsa=None)` | Opens an `OpenQuoteContext` — probes all hosts, picks fastest, sets up RSA |
| `create_trade_context(is_rsa=None, **kwargs)` | Opens an `OpenSecTradeContext` — reuses the same probe result as the quote context |
| `get_demo_trade_password()` | Returns `FUTU_TRADE_PWD` — use only with SIMULATE account |
| `clear_connection_cache()` | Forces the next context creation to re-probe all hosts |

**Connection flow:**

1. `create_quote_context()` calls `connect_opend()` which TCP-probes all hosts in parallel
2. Sorts by latency, picks the fastest
3. Attempts connection with the configured RSA setting
4. If RSA fails and `is_rsa=None` (auto mode), retries without RSA
5. Stores the winning `(info, actual_rsa)` in a module-level cache
6. `create_trade_context()` reads from that cache — no redundant TCP probe

`00_connect_ha/main.py` contains the full standalone HA algorithm if you need to see it in isolation.
