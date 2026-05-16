# futu-python-samples — AGENTS.md

## What This Project Is

**97** standalone examples for the Futu OpenAPI Python SDK. Every script fires real API calls against a live OpenD gateway — no mocks, no stubs.

**Repo:** `https://github.com/shing1211/futu-python-samples`
**SDK docs:** https://openapi.futunn.com/futu-api-doc/

## Running Examples

Full categorized index → [README.md](README.md) → [examples/README.md](examples/README.md)

```bash
# Single example
python3 examples/07_kline/main.py

# Full suite with PASS/FAIL report
python3 scripts/run_all.py

# Quick smoke test
bash scripts/test_all.sh
```

## Key Documentation

| Document | What it covers |
|----------|---------------|
| [README.md](README.md) | Project overview, 97-example index, quick start, configuration |
| [examples/README.md](examples/README.md) | Full categorized example index with descriptions |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, directory tree, handler class table, Mermaid diagrams |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Connection, RSA, trade lockout, quota, pandas pitfalls |
| [CHANGELOG.md](CHANGELOG.md) | Version history v1.0.0–v1.5.0 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Adding examples, code conventions, testing |
| [PLANS.md](PLANS.md) | Implementation specs for all 39 advanced examples (all complete) |
| [AGENTS.md](AGENTS.md) | ← You are here. SDK quirks reference for AI coding tools |

## ⚠️ SDK Quirks — These Will Bite You

> Duplicated from README.md for tool visibility. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for full detail.

### Return types that differ from the docs

- **`get_history_kl_quota()`** → `(used: int, remain: int, None)` not dict
- **`request_history_kline()`** → 3-tuple `(ret, df, next_page_token)` not 2-tuple
- **`get_warrant()`** → `(df, has_more, total)` — handle pagination
- **`subscribe()`/`unsubscribe()`** → `(ret_code, None)` tuple, not bare int
- **`get_order_book()`** → `{"Bid": [...], "Ask": [...]}` dict of 3-tuples, not DataFrame

### Enum names that don't exist

| Docs imply | Reality |
|------------|---------|
| `ft.AuType.BFQ` | Use `ft.AuType.HFQ` (no adj.) or `ft.AuType.QFQ` (adjusted) |
| `ft.PriceReminderOp` | It's `ft.SetPriceReminderOp` |
| `ft.SecurityReferenceType.BULL_BEAR` | Not available — guard with `try/except` |

### pandas traps

```python
# ✗ hist[-1]          → KeyError; use hist.iloc[-1]
# ✗ if df: ...        → ValueError; use if df is not None and not df.empty
# ✗ plate_df['name']  → KeyError; use plate_df['plate_name']
```

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **futu-python-samples** (3180 symbols, 4390 relationships, 99 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
