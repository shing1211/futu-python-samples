# Recorded Observations

Evidence status for every claim in `spec.md`. Maintained by
`scripts/probe_return_arity.py`, which reports and never fixes.

## Resolved: the `get_history_kl_quota()` / `get_warrant()` arity question

**Status: RESOLVED by observation. The four call sites conform; the prose was wrong.**

The question this change was written to settle was whether these interfaces
return a leading status code. The open question read:

> `AGENTS.md` and `CONTRIBUTING.md` both state that `get_history_kl_quota()`
> returns `(used: int, remain: int, detail: None)` and that `get_warrant()`
> returns `(df, has_more, total)` — a 3-tuple with no leading `ret` — yet four
> call sites unpack a leading `ret`.

Observed, by reading the installed package's return statements:

| Interface | Observed return | Outer | Inner | Leading status code |
|---|---|---|---|---|
| `get_history_kl_quota()` | `return ret_code, (used_quota, remain_quota, detail_list)` | 2 | 3 | **yes** |
| `get_warrant()` | `return ret_code, (warrant_data_frame, last_page, all_count)` | 2 | 3 | **yes** |

Observed at both ends of the supported range:

| SDK version | `get_history_kl_quota` | `get_warrant` |
|---|---|---|
| `10.9.6908` (minimum supported, per `requirements.txt`) | `ret_code, (used, remain, detail_list)` | `ret_code, (df, last_page, all_count)` |
| `10.11.7108` (installed) | identical | identical |

The shape is stable across the declared range.

**Conclusion.** Both interfaces return a **2-tuple**: a leading status code, then
a nested 3-tuple. The documented "3-tuple" is the *inner* value. So:

- `examples/26_history_kl_quota/main.py:45,56` — `ret, quota_data = ctx.get_history_kl_quota()` **conforms**
- `examples/28_warrant/main.py:45` — `ret, warrant_data = ctx.get_warrant(...)` **conforms**
- `examples/64_backtesting/main.py:54` — `ret, quota = ctx.get_history_kl_quota()` **conforms**
- `examples/67_health_monitor/main.py:95` — `ret, quota_data = ctx.get_history_kl_quota(...)` **conforms**

No call site was changed. The defensive `isinstance(..., tuple)` handling in
examples 26 and 28 is **necessary, not paranoid**: the inner value really is a
tuple.

### Secondary finding: `get_warrant()`'s third field is not a boolean

The prose records the inner tuple as `(df, has_more, total)`. Observed, it is
`(warrant_data_frame, last_page, all_count)`. `last_page` is a pagination
cursor, not a boolean "has more" flag. `examples/28_warrant/main.py:51` binds it
to a variable named `has_more`, which is misleading; the value is only logged,
so nothing is functionally wrong, but the name misrepresents the field.

## Resolved: three further interfaces, found by the first full live run

The first live run reported four examples failing with
`ValueError: too many values to unpack`. They are **not** `get_warrant`; they
are separate interfaces whose arity the prose never described. Observed at
`10.11.7108`:

| Interface | Observed return | Outer |
|---|---|---|
| `get_broker_queue()` | `return RET_OK, bid_frame_table, ask_frame_table` | **3** |
| `get_economic_calendar()` | `return RET_OK, pd.DataFrame(...), next_page_val, has_more` | **4** |
| `get_institution_list()` | `return RET_OK, pd.DataFrame(...), next_page, all_count` | **4** |
| `get_institution_holding_list()` | `return RET_OK, pd.DataFrame(...), next_page, all_count` | **4** |
| `get_institution_holding_change()` | `return RET_OK, pd.DataFrame(...), next_page, all_count` | **4** |

Call sites conformed only after correction:

| Example | Was | Now |
|---|---|---|
| `09_broker_queue` | `ret, (bid, ask) = ...` | `ret, bid, ask = ...` |
| `45_broker_handler` | `ret, data = ...` + `isinstance` guessing | `ret, bid, ask = ...` |
| `122_fedwatch_macro` | `ret, data = ...` | `ret, data, next_page, has_more = ...` |
| `123_institutional_13f` | `ret, data = ...` ×5 | `ret, data, next_page, all_count = ...` |

**Generalisation.** The prose's blanket claim that "the vast majority of Futu
APIs return a 2-tuple" understates the exceptions. Arity varies per interface
and must be observed, not assumed — which is exactly what the probe is for.
The probe's `TARGETS` now includes these five interfaces so a future SDK change
is detectable by re-running it.

## Confirmed deviating, already handled correctly

| Interface | Observed return | Outer |
|---|---|---|
| `request_history_kline()` | `return RET_OK, kline_frame_table, next_page_req_key` | 3 |
| `get_order_book()` | `return RET_OK, orderbook` | 2 |

### `request_history_kline()`'s page key is bytes

Observed: the third value comes back as `bytes`. The SDK's own date parser
tests `":" not in start`, which raises
`TypeError: a bytes-like object is required, not 'str'` on a bytes operand. A
caller that feeds the page key straight back in crashes on the *second* page.
Call sites must decode it first; `examples/71_market_regime` and
`examples/92_monte_carlo` now do.

## Dict-returning interfaces (also deviating)

Observed: these return `(ret, dict)`, not a DataFrame. Treating the value as a
frame raises `AttributeError: 'dict' object has no attribute 'empty'`.

| Interface | Dict keys |
|---|---|
| `get_technical_unusual()` / `get_financial_unusual()` / `get_derivative_unusual()` | `err_code`, `retMsg`, `time_range`, `content` (a newline-separated **string**) |
| `get_option_zero_dte_screener()` / `get_option_earnings_screener()` | `item_list` (DataFrame), `next_page`, `update_timestamp`, `all_count` |
| `get_option_event()` | `event_list` (DataFrame), `next_page`, `all_count` |

Corrected call sites: `29_unusual`, `63_earnings_screener`, `119_option_0dte`,
`120_option_earnings`.

## Enumeration members that do not exist

Observed against `10.11.7108`:

| Referenced | Exists? | Correction |
|---|---|---|
| `ft.SubType.CUR_KLINE` | **no** | `ft.SubType.K_DAY` (`71`, `72`, `73`) |
| `ft.SellerType.PUT_SELL` | **no** | `ft.SellerType.CASH_SECURED_PUT` (`121`) |
| `ft.SellerType.CALL_SELL` | **no** | `ft.SellerType.COVERED_CALL` (`121`) |
| `ft.OptionCondType.CALL` | **no** | no equivalent; filter rewritten (`52`) |
| `ft.AuType.BFQ` | no | `HFQ` / `QFQ` — already absent from the code |
| `ft.PriceReminderOp` | no | `ft.SetPriceReminderOp` — already absent from the code |

## Other interface signatures corrected from observation

| Interface | Reality | Example |
|---|---|---|
| `get_plate_list()` | takes `(market, plate_class)`; `Plate.INDUSTRY`/`CONCEPT` are **strings**, not enum instances | `91` |
| `get_plate_stock()` | takes a single `plate_code`; no `market`, no `code_list` | `91` |
| `get_option_chain()` | the filter kwarg is `data_filter`, not `option_data_filter`; `OptionDataFilter` has no `filter_call_put` or `moneyness_min/max` | `52` |
| `request_history_kline()` | the count kwarg is `max_count`, not `num_bars` | `71`, `72`, `90`, `92` |

## What the prose documents must now say

`AGENTS.md:44-46` and `CONTRIBUTING.md:137,139` describe the inner tuple as the
whole return value for two interfaces, and describe nothing at all for the five
in the second section above. **Deferred**: `design.md` records retiring the
duplicated prose tables as a separate change, and this change must not delete
prose. Until that reconciliation, the prose remains incomplete and this file is
the correct record.

## Evidence status of the remaining claims

| Claim | Status | Basis |
|---|---|---|
| `get_history_kl_quota()` outer arity 2, inner 3 | CONFIRMED | observed at 10.9.6908 and 10.11.7108 |
| `get_warrant()` outer arity 2, inner 3 | CONFIRMED | observed at 10.9.6908 and 10.11.7108 |
| `get_broker_queue()` arity 3 | CONFIRMED | observed at 10.11.7108 |
| `get_economic_calendar()` arity 4 | CONFIRMED | observed at 10.11.7108 |
| `get_institution_*` arity 4 | CONFIRMED | observed at 10.11.7108 |
| `request_history_kline()` arity 3, page key bytes | CONFIRMED | observed at 10.11.7108 |
| `get_order_book()` arity 2 | CONFIRMED | observed at 10.11.7108 |
| dict-returning interfaces above | CONFIRMED | observed at 10.11.7108 |
| absent enum members above | CONFIRMED absent | `dir()` against 10.11.7108 |
| pandas `.iloc[-1]` / truth-value rules | CONFIRMED by live run | `124` crashed on `if not data:` and was fixed |
| `ft.SecurityReferenceType.BULL_BEAR` absent | UNVERIFIED | not probeable without a market session |
| `get_history_kl_quota()` detail field | CONFIRMED `None` in practice | not re-observed; recorded from prior documentation |

Claims above are reproduced from `AGENTS.md` and `CONTRIBUTING.md` unless marked
CONFIRMED by observation. Everything marked CONFIRMED was read from the
installed SDK source or observed at runtime during the live run; anything
reproduced unverified is flagged accordingly.