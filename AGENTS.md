# futu-python-samples — AGENTS.md

## Project Overview

42 verified standalone examples for the Futu OpenAPI Python SDK (`futu-api`).
Each example demonstrates one SDK function or feature — all run against a live OpenD gateway.

**Repo**: `https://github.com/shing1211/futu-python-samples`
**SDK docs**: https://openapi.futunn.com/futu-api-doc/

## Running Examples

```bash
# Single example
python3 examples/07_kline/main.py

# All 42 examples (recommended runner)
python3 scripts/run_all.py

# Smoke test all
bash scripts/test_all.sh
```

## Configuration

All config via `.env` in the repo root:

| Variable | Description | Default |
|----------|-------------|---------|
| `FUTU_OPEND_HOSTS` | `host:port:is_rsa[,...]` HA list | `127.0.0.1:11111` fallback |
| `FUTU_ADDR` | Single host fallback | `127.0.0.1:11111` |
| `FUTU_RSA_KEY` | RSA private key path | `/etc/futu/keys/private_key.pem` |
| `FUTU_TCP_TIMEOUT` | TCP probe timeout (s) | `3` |
| `FUTU_TRADE_PWD` | SIMULATE unlock password | `123456` |

Remote gateways (non-localhost) require RSA. The `is_rsa` flag in `FUTU_OPEND_HOSTS`
controls per-host RSA mode. No auto-detection exists — RSA is purely client-side opt-in.

## Critical SDK Quirks (verified against live gateway)

> SDK docs often lag the actual API behavior. These are verified facts from live testing.

**Return types differ from docs:**
- `get_history_kl_quota()` → `(int, int, None)` tuple
- `request_history_kline()` → `(ret, DataFrame, next_page_token)` **3-tuple**
- `get_warrant()` → `(DataFrame, bool, int)` tuple
- `get_order_book()` → `(ret, dict)` where entries are `(price, vol, count, extra_dict)` 4-tuples
- `subscribe()` → `(ret_code, None)` 2-tuple — unpack as `ret, _ = ctx.subscribe(...)`

**Enum name differences:**
- `AuType.BFQ` → `AuType.HFQ` (HFQ = no adjustment, QFQ = adjusted)
- `PriceReminderOp` → `SetPriceReminderOp`
- `SecurityReferenceType.BULL_BEAR` → **does not exist**

**pandas gotchas:**
- `hist[-1]` on Series → `KeyError` — use `hist.iloc[-1]`
- `if df:` on DataFrame → ambiguous truth — use `if df is not None and not df.empty:`

**DataFrame column names:**
- `get_plate_list()` → `plate_name` not `name`
- `get_capital_flow()` → `capital_flow_item_time`, `in_flow` etc.

**Parameter names:**
- `unsubscribe()` → `code_list=` not `codes=`
- `get_capital_flow()` → no `period_type` parameter

**Push handlers:**
- `OrderBookHandlerBase` content → dict with `Bid`/`Ask` keys; each level is 3-tuple
- `SysNotifyHandlerBase` content → `(main_type, sub_type, msg)`

## Architecture

All examples (except `00`) import from `examples/connect.py`:
- `create_quote_context()` — HA gateway selection + RSA config
- `create_trade_context()` — reuses cached gateway probe
- `get_demo_trade_password()` — returns `FUTU_TRADE_PWD`
- `clear_connection_cache()` — force re-probe

`connect.py` does parallel TCP probes across all `FUTU_OPEND_HOSTS` entries,
picks the fastest reachable host, and retries RSA on failure. Probe result is cached
so both quote and trade contexts connect to the same gateway without redundant probing.
