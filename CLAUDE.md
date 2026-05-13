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

## Project: futu-python-samples

42 verified examples for the Futu OpenAPI Python SDK.

### Config (`.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `FUTU_OPEND_HOSTS` | `host:port:is_rsa[,...]` HA list | `127.0.0.1:11111` fallback |
| `FUTU_ADDR` | Single host fallback | `127.0.0.1:11111` |
| `FUTU_RSA_KEY` | RSA private key path | `/etc/futu/keys/private_key.pem` |
| `FUTU_TCP_TIMEOUT` | TCP probe timeout (s) | `3` |
| `FUTU_TRADE_PWD` | SIMULATE unlock password | `123456` |

### Critical SDK quirks

- `get_history_kl_quota()` → `(int, int, None)` tuple, not dict
- `request_history_kline()` → 3-tuple `(ret, DataFrame, next_page_token)`
- `get_warrant()` → `(DataFrame, bool, int)` tuple
- `get_order_book()` → dict with 4-tuple `(price, vol, count, extra)` entries
- `subscribe()` → `(ret_code, None)` — unpack `ret, _ = ctx.subscribe(...)`
- `AuType.BFQ` does not exist — use `AuType.HFQ` or `AuType.QFQ`
- `SetPriceReminderOp` (not `PriceReminderOp`)
- `SecurityReferenceType.BULL_BEAR` — does not exist
- `hist[-1]` on pandas Series → `KeyError` — use `hist.iloc[-1]`
- `get_capital_flow()` → no `period_type` param; columns: `capital_flow_item_time`, `in_flow`

### Architecture

All examples (except `00`) import from `examples/connect.py`:
- `create_quote_context()` — HA gateway selection + RSA config
- `create_trade_context()` — reuses cached gateway probe
- `get_demo_trade_password()` — returns `FUTU_TRADE_PWD`
- `clear_connection_cache()` — force re-probe

### Test

```bash
python3 scripts/run_all.py    # recommended — full runner
bash scripts/test_all.sh      # delegates to run_all.py
```
