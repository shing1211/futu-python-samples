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

This project is indexed by GitNexus as **futu-python-samples**. Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.
<!-- gitnexus:end -->
