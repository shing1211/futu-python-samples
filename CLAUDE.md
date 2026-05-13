<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **futu-python-samples** (324 symbols, 455 relationships, 6 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/futu-python-samples/context` | Codebase overview, check index freshness |
| `gitnexus://repo/futu-python-samples/clusters` | All functional areas |
| `gitnexus://repo/futu-python-samples/processes` | All execution flows |
| `gitnexus://repo/futu-python-samples/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

---

# futu-python-samples

42 verified examples for the Futu OpenAPI Python SDK. Every script fires live API calls — no mocks.

## Project Config

| Variable | What it does | Default |
|----------|-------------|---------|
| `FUTU_OPEND_HOSTS` | `host:port:is_rsa[,...]` HA gateway list | falls back to `FUTU_ADDR` |
| `FUTU_ADDR` | Single host fallback | `127.0.0.1:11111` |
| `FUTU_RSA_KEY` | RSA private key path | `/etc/futu/keys/private_key.pem` |
| `FUTU_TCP_TIMEOUT` | TCP probe timeout | `3` seconds |
| `FUTU_TRADE_PWD` | SIMULATE unlock password | `123456` |

Remote gateways require RSA. There is **no localhost-vs-remote auto-detection** — set `is_rsa=True` in `FUTU_OPEND_HOSTS` for remote hosts.

## ⚠️ SDK Quirks to Watch For

**Return types that differ from the docs:**

- `get_history_kl_quota()` → `(used: int, remain: int, None)` — plain 3-tuple, not a dict
- `request_history_kline()` → `(ret, DataFrame, next_page_token)` — 3-tuple, third value is a pagination cursor
- `get_warrant()` → `(DataFrame, has_more: bool, total: int)` — 3-tuple
- `get_order_book()` → `(ret, dict)` where dict entries are `(price, vol, count, extra)` 4-tuples
- `subscribe()` → `(ret_code, None)` — unpack as `ret, _ = ctx.subscribe(...)`
- `request_trading_days()` → plain `list[str]` — no tuple wrapper at all

**Enum names that don't exist:**

- `ft.AuType.BFQ` → `ft.AuType.HFQ`
- `ft.PriceReminderOp` → `ft.SetPriceReminderOp`
- `ft.SecurityReferenceType.BULL_BEAR` → **not available**

**pandas traps:**

- `hist[-1]` on a Series → `KeyError` — use `hist.iloc[-1]`
- `if df:` on a DataFrame → `ValueError` — use `if df is not None and not df.empty:`

**Column and parameter names:**

- `get_plate_list()` → column is `plate_name`, not `name`
- `get_capital_flow()` → no `period_type` param; columns are `capital_flow_item_time`, `in_flow`
- `subscribe/unsubscribe` → parameter is `code_list=`, not `codes=`

## Architecture

`examples/connect.py` is the shared HA connection module.

| Function | What it does |
|----------|-------------|
| `create_quote_context(is_rsa=None)` | Probes all hosts, picks fastest, configures RSA, returns `OpenQuoteContext` |
| `create_trade_context(is_rsa=None, **kwargs)` | Reuses cached probe result, returns `OpenSecTradeContext` |
| `get_demo_trade_password()` | Returns `FUTU_TRADE_PWD` — SIMULATE only |
| `clear_connection_cache()` | Force a fresh probe on the next context creation |

The HA algorithm probes all hosts in parallel, sorts by TCP latency, attempts the connection, retries without RSA on failure. The result is cached so both quote and trade contexts land on the same gateway.

## Test

```bash
python3 scripts/run_all.py    # recommended — full runner with PASS/FAIL
bash scripts/test_all.sh      # delegates to run_all.py
```
