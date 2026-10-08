# Tasks

## 1. Static Verification Tier — Scaffolding

- [x] 1.1 Create the static check module with a check registry, a discovery routine that enumerates example directories from the filesystem, and a CLI entry point; verify `--list` prints every registered check name and exits 0, and that discovery returns 129 directories with no directory named from a hand-maintained list
- [x] 1.2 Give the static tier a verdict channel distinct from the live tier's, emitting its own summary and exit status; verify running it on a clean tree exits 0 and that its output is labeled with the tier name in a way that cannot be read as a live-tier result

## 2. Static Verification Tier — Source Property Checks

Each check implements one property from the closed set in `design.md` Decision 5. Each reports findings and never asserts runtime behavior.

- [x] 2.1 Implement the byte-compilation check over every example file; verify a test with a deliberately unparseable fixture reports exactly that file, and a clean tree reports zero findings
- [x] 2.2 Implement the license-header presence check as report-only, measuring coverage rather than gating; verify a test with a headerless fixture reports it, and that running the check against the repository today surfaces the 16 known headerless files under `examples/99_financial_statements` through `examples/114_valuation_heatmap` — note that promoting this check to a failing gate is blocked until those files are fixed, which is out of scope for this change
- [x] 2.3 Implement the example-skeleton check covering the `__main__` guard, `sys.path` insertion preceding `futu` and `connect` imports, and context cleanup on every context-creating path; verify tests report the two currently unguarded examples (`examples/56_order_flow_imbalance`, `examples/94_earnings_analyzer`) and a fixture with import ordering inverted
- [x] 2.4 Implement the error-suppression check, finding exception handlers whose body is only `pass` or `continue`; verify a test asserts it flags the five handlers in `examples/67_health_monitor` and a fixture whose handler logs and re-raises is not flagged
- [x] 2.5 Implement the dead-constant check, finding uppercase module-level assignments never read; verify a test asserts it flags `TRADE_EXAMPLES` in `scripts/run_all.py` today and does not flag a constant that is read
- [x] 2.6 Implement the index-coverage check, comparing example directories against the example index and detecting examples indexed in more than one section; verify a test asserts it reports the 26 directories absent from the index and the 8 indexed in two sections, and reports zero directories indexed but absent from the filesystem
- [x] 2.7 Implement the contract-table duplication check, detecting return-shape, enum, and pandas tables present in more than one document; verify a test asserts it flags the tables shared by `AGENTS.md` and `CONTRIBUTING.md` — this check reports duplication as debt and does not reconcile the prose, which is a follow-up change
- [x] 2.8 Add unit tests for the registry and runner covering a passing run, a run with findings, and an unknown-check-name invocation; verify the suite passes and that each of checks 2.1 through 2.7 has at least one test asserting its real behavior against a fixture rather than a stub

## 3. Live Verification Tier — Verdict Derivation

Rework `scripts/run_all.py` per `design.md` Decisions 2, 3, and 4. Behavior is unchanged until this group lands; it changes verdicts.

- [x] 3.1 Make a non-zero exit an unconditional failure, and restrict output inspection to reclassifying a failure as blocked or as an expected timeout; verify a test runs a fixture that exits non-zero with empty stderr and asserts it is reported as FAIL, and a fixture that exits zero and is reported PASS
- [x] 3.2 Replace the keyword-matching classifier, removing the substring list that currently decides pass and fail; verify a test asserts no verdict is derived from the presence or absence of any specific word in captured output
- [x] 3.3 Introduce the four outcome states PASS, FAIL, BLOCKED, and NOT-VERIFIED, and stop counting blocked or not-verified examples toward the pass total; verify a test asserts a trade-lockout refusal yields BLOCKED and that the pass total excludes it
- [x] 3.4 Derive the example set from the filesystem and report any directory not run as NOT-VERIFIED; verify a test asserts the reported set equals the directory listing and that an intentionally excluded directory appears as NOT-VERIFIED rather than passing
- [x] 3.5 Remove the unconsulted `TRADE_EXAMPLES` set and express its intent as the BLOCKED outcome; verify the dead-constant check from 2.5 reports zero findings for `scripts/run_all.py`
- [x] 3.6 Remove the private-range host and key-path defaults the runner injects into child environments, and stop overriding a caller's configured values; verify a test asserts a runner invocation with a configured host reaches the child process unchanged
- [x] 3.7 Make `PUSH_EXAMPLES` and `SLOW_EXAMPLES` consulted classifications and assert at startup that every named directory exists; verify a test asserts a classification naming a nonexistent directory fails fast, and that a timeout is reported as expected only for declared-unbounded examples and as a failure otherwise
- [x] 3.8 Add tests covering the exit-status, outcome-state, set-derivation, and classification behaviors above; verify the suite passes and that the full 129-example run reports every directory as one of the four states with no directory silently absent

## 4. Example Conformance

- [x] 4.1 Correct the error-suppression sites reported by check 2.4, starting with `examples/67_health_monitor`, so each suppressed failure is recorded and either re-raised or narrowed to a case genuinely handled; verify check 2.4 reports zero suppression sites, or that each remaining site carries a recorded justification
- [x] 4.2 Add the `__main__` guard to `examples/56_order_flow_imbalance` and `examples/94_earnings_analyzer`; verify check 2.3 reports zero unguarded examples
- [x] 4.3 Record the outcome of 4.1 and 4.2 in the contributing documentation, including how a contributor suppresses an error legitimately; verify the documented pattern is exercised by at least one example that check 2.4 accepts

## 5. SDK Return-Arity Probe

- [x] 5.1 Implement the probe for the return arity of `get_history_kl_quota()` and `get_warrant()`, preferring runtime observation against a live gateway and falling back to source inspection of the installed package, reporting the observed arity and its evidence source; verify a test asserts the probe reports unresolved when neither gateway nor SDK is available, and that it makes no code change
- [x] 5.2 Run the probe and record the observed arity, the evidence source, and the SDK version in `specs/sdk-return-contracts/spec.md`, replacing the recorded open question; verify the spec no longer lists the question as unresolved, or records it as unresolved with the unavailable dependency named
- [x] 5.3 Conform the four call sites to the probe's observation — `examples/26_history_kl_quota`, `examples/28_warrant`, `examples/64_backtesting`, `examples/67_health_monitor` — removing the outer unpacking arity that the observation contradicts while keeping the existing defensive handling; verify a test asserts each call site unpacks exactly the observed arity
- [x] 5.4 Confirm the four call sites are no longer enumerated as non-conforming; verify `specs/sdk-return-contracts/spec.md` contains no call site listed as contradicting a recorded shape, and that the live tier reports the four examples against a live gateway

## 6. Continuous Integration and Documentation

- [x] 6.1 Add a CI workflow that runs the static tier only, with the tier named in the check title so a green result is not read as evidence that examples work; verify the workflow runs green on the current tree and that its title states which tier it ran
- [x] 6.2 Resolve whether `black` and `ruff` are enforced gates or advisory, and configure the static tier's severity accordingly; verify the configured severity is observable in the tier's output for a style finding, and that the decision is recorded in the contributing documentation
- [x] 6.3 Document both verification tiers, the four outcome states, and the gateway-free scope boundary in the contributing documentation; verify a reader can determine from the documentation alone which properties each tier asserts and which it cannot
- [x] 6.4 Record the duplication between the `AGENTS.md` and `CONTRIBUTING.md` contract tables as known debt, naming this change as the artifact that will eventually replace them; verify the debt is recorded and that no prose table was deleted or edited by this change

## 7. Integration

- [x] 7.1 Run both tiers end to end and confirm the pass total counts only examples that ran and demonstrated their behavior, with blocked and not-verified reported separately; verify the summary reports all four states and that no example is silently absent
- [x] 7.2 Confirm the static tier's findings against the known defect set — 16 headerless files, one dead constant, 26 unindexed directories, 8 doubly-indexed examples — and confirm each is reported; verify the run output names every one of them
- [x] 7.3 Amend the scope paragraph of `proposal.md`, which states this change adds specification only and defers remediation, to match the implemented scope recorded in `design.md`; verify the proposal no longer contradicts the presence of design, tasks, and an applicable change

## 8. Gateway Connection Configuration

Fixes the root cause of the live run's all-BLOCKED result: a misconfigured RSA key surfaced as an indefinite SDK retry and therefore as a timeout, because the fallback in `connect_opend` cannot run until the first attempt returns.

- [x] 8.1 Validate the RSA key inside `configure_rsa()`; when RSA is enabled and the configured key path is missing or unreadable, raise an error naming the path tried plus `FUTU_RSA_KEY` and `FUTU_OPEND_HOSTS`, raised before any `OpenQuoteContext` is constructed; verify a test with a nonexistent key raises before the context is built, a test with a readable key proceeds, and a test with RSA disabled does not read the key
- [x] 8.2 Change the `FUTU_ADDR` fallback in `_parse_hosts()` to resolve `is_rsa=True` so it matches the host-list branches; verify a test asserts the same host configured through `FUTU_ADDR` and through `FUTU_OPEND_HOSTS` resolves to the same RSA assumption, and that an explicit `is_rsa=False` still overrides the default
- [x] 8.3 Restrict the `check sha error` and `init connect fail` patterns to the timeout path, keeping the unambiguous refusal patterns on both paths; verify a test asserts a non-zero exit printing `check sha error` is FAIL while a timeout with the same text is BLOCKED
- [x] 8.4 Correct `.env.example`: state that the RSA key is required whenever the gateway sets `<rsa_private_key>`, including a local gateway; replace the private-range example hosts with a neutral one; verify the file states the local-gateway RSA case and contains no private-range host
- [x] 8.5 Add tests covering 8.1, 8.2, and 8.3; verify the full suite passes and that no test asserts the superseded behaviour
- [x] 8.6 Document the RSA requirement and the single-host RSA default in `CONTRIBUTING.md`; verify the documented requirement matches `.env.example` and that the `is_rsa=False` escape hatch is documented

## 9. Remediation Found by the Full Live Run

Scope approved during apply, after the first full live run reported 50 failures that the superseded runner had reported as pass. Corrections are pinned by tests; see `specs/sdk-return-contracts/observations.md` for the observed interface shapes.

- [x] 9.1 Extend the arity probe to the interfaces the live run found deviating (`get_broker_queue`, `get_economic_calendar`, `get_institution_*`); verify the probe reports an outer arity for each and the test derives its expectation from `TARGETS`
- [x] 9.2 Correct the arity call sites in `09_broker_queue`, `45_broker_handler`, `122_fedwatch_macro`, and `123_institutional_13f`; verify each unpacks the observed outer arity and all four pass against a live gateway
- [x] 9.3 Correct call sites that treat a returned dict as a DataFrame in `29_unusual`, `63_earnings_screener`, `119_option_0dte`, `120_option_earnings`; verify all four pass
- [x] 9.4 Correct the `num_bars` keyword to `max_count` for `request_history_kline` in `71_market_regime`, `72_candlestick_scanner`, `90_ah_premium`, `92_monte_carlo`; verify all four pass
- [x] 9.5 Decode the bytes page key returned by `request_history_kline` before feeding it back in; verify `71_market_regime` and `92_monte_carlo` complete their pagination
- [x] 9.6 Correct the absent enum members `SubType.CUR_KLINE`, `SellerType.PUT_SELL`/`CALL_SELL`, and the `OptionCondType` misuse; verify `52`, `71`, `72`, `73`, `121` pass
- [x] 9.7 Correct the `get_plate_list` / `get_plate_stock` / `get_option_chain` signatures and the pandas truth-value trap in `124_industry_chain`; verify `52`, `91`, `124` pass
- [x] 9.8 Guard the quota-delta format in `43_subscribe_lifecycle` against a `None` reading; verify it passes
- [x] 9.9 Classify the genuinely unbounded examples (`58`, `71`, `72`, `73`) and give the bounded-but-slow examples a ceiling above their measured runtime; verify `48`, `54`, `56`, `57` pass and `58` reports the expected outcome
- [x] 9.10 Add the invariant tests that the classifications are disjoint, that slow ceilings exceed the default, and that a not-terminating example contains an unbounded loop; verify the suite passes and that the tests caught the five misclassified push examples
- [x] 9.11 Broaden the trade-unlock pattern to the gateway's Chinese cooldown message; verify a test asserts both spellings classify as blocked and that a successful unlock still passes
