# Design

## Context

See `proposal.md` — Why for motivation, and `specs/example-verification/spec.md` and `specs/sdk-return-contracts/spec.md` for the requirements. This document covers only how.

Current state that constrains the approach:

- `scripts/run_all.py` is a single 209-line module with three hand-maintained name sets (`TRADE_EXAMPLES`, `PUSH_EXAMPLES`, `SLOW_EXAMPLES`). Only two are consulted. It injects default environment values including a private-range host list, then classifies each example by substring-matching captured stderr.
- Every example requires a live OpenD gateway, so the harness has no gateway-free execution path. The SDK is not importable in every environment that would run the harness.
- The project states a value of "no mocks, no stubs" in `AGENTS.md`, which rules out a stub gateway.
- 127 of 129 examples guard execution under `if __name__ == "__main__":`; two do not. No example performs API calls at import time.
- Four call sites disagree with the documented return arity of `get_history_kl_quota()` and `get_warrant()`, and the SDK is not importable in the authoring environment.
- There is no CI workflow, and no test files, despite `pytest`, `black`, and `ruff` being declared as dev dependencies and `black`/`ruff` already configured in `pyproject.toml`.
- `FutuOpenD` retries an unsuccessful protocol handshake internally and indefinitely, so `OpenQuoteContext(...)` does not return promptly on a handshake failure. This defeats the RSA ON/OFF fallback in `connect_opend`, which cannot run until the first attempt returns.
- A local `FutuOpenD` configured with `<rsa_private_key>` in its XML requires clients to negotiate RSA, so "localhost implies no RSA" is false. The RSA private key is not a remote-only concern.

## Goals / Non-Goals

**Goals:**

- Make a passing verification run mean something: a pass count that reflects examples which ran and demonstrated their behavior.
- Make verification runnable without a gateway for the subset of properties that do not require one, so regressions are catchable outside the maintainer's machine.
- Resolve the `get_history_kl_quota()` / `get_warrant()` arity question by observation, and bring the four contradicting call sites into conformance.
- Convert the duplicated prose contract tables into a single artifact with per-claim evidence status, without deleting the prose during this change.

**Non-Goals:**

- Mocking or stubbing OpenD. Explicitly rejected; see Decision 1.
- Correcting the example bodies beyond the four call sites and the error-suppression sites the static tier flags. Broader cleanup is a follow-up.
- Reconciling `AGENTS.md` and `CONTRIBUTING.md` against the new spec artifact. This change leaves both prose tables in place and records the duplication as debt; retiring them is a separate change.
- Fixing the licensing defects found during review (`pyproject.toml` declaring MIT against an Apache-2.0 `LICENSE`, and 16 example files missing the Apache header). Unrelated to these two capabilities.
- Making the full 129-example suite fast. The live tier remains slow and serial; parallelism is out of scope.

## Decisions

### Decision 1: Two verification tiers, no stub gateway

**Choice.** Split verification into a *live tier* that runs examples against a real gateway and asserts behavior, and a *static tier* that runs with no gateway and asserts only what is decidable from source. The stub-gateway option was considered and rejected because `AGENTS.md` states the project fires real API calls with "no mocks, no stubs"; overriding that value is a project-level decision, not an implementation detail, and it was not taken.

**Why this split.** The properties that most need catching need no gateway. The 16 files missing the Apache header, the unconsulted `TRADE_EXAMPLES` set, and the 26 example directories absent from the index are all decidable statically. A live-only design leaves the repository exactly as unverifiable as it is today; a stub design contradicts a stated project value.

**Boundary.** The static tier asserts nothing about runtime behavior. It cannot and will not claim an example works. Its output is a separate verdict channel from the live tier's, and neither is allowed to imply the other.

### Decision 2: Exit status is the primary verdict signal, and output inspection may only downgrade

**Choice.** A non-zero exit is a failure, unconditionally. Inspection of captured output may reclassify a *failure* as blocked or as an expected-timeout, but may never reclassify a failure as a pass.

**Why.** The current classifier inverts this: it treats absence of failure-indicating text as evidence of success. Inverting the direction of the only signal the harness controls is the minimum change that makes a crash with empty output detectable. The asymmetry is deliberate — the harness has direct evidence of failure and only absence of evidence of success, and those are not equivalent.

**Alternative considered.** Making any heuristic verdict authoritative. Rejected: it preserves the failure mode that produced the current defect.

### Decision 3: Four outcome states, with blocked distinct from pass

**Choice.** Report PASS, FAIL, BLOCKED, and NOT-VERIFIED. BLOCKED covers external-state refusals — unavailable gateway, unauthenticated session, gateway cooldown after repeated failed unlocks. NOT-VERIFIED covers an example the harness did not run.

**Why.** The runner currently reports a trade-lockout as `PASS (— trade locked)`, which inflates the pass count with examples that demonstrated nothing. BLOCKED preserves the useful signal — "this example is fine, the gateway is refusing it" — without letting that count as evidence.

**Alternative considered.** A single SKIPPED state merging blocked and not-verified. Rejected: "the gateway refused it" and "the harness never ran it" have different causes and different fixes, and collapsing them would hide the not-verified case that Decision 5 depends on.

### Decision 4: The verified set is derived from the repository, never from a hand-maintained list

**Choice.** Enumerate examples by scanning example directories, and report any directory not run as NOT-VERIFIED. Remove `TRADE_EXAMPLES`; retain `PUSH_EXAMPLES` and `SLOW_EXAMPLES` but make them consulted, asserted-on-use classifications.

**Why.** `TRADE_EXAMPLES` is the concrete evidence that hand-maintained sets rot: it survived multiple refactors while never being read, and its existence in the module implied a skipping behavior the module does not implement. Deriving the set from the filesystem removes the failure mode rather than fixing one instance.

**Alternative considered.** Keeping the lists and adding a test that every list member exists. Rejected: it checks list-to-filesystem agreement while leaving the harness free to never consult the list, which is the actual defect.

### Decision 5: The static tier decides a defined, closed set of properties

**Choice.** The static tier checks, and only checks: byte-compilation of every example; the presence of the required license header; the documented example skeleton, including the `__main__` guard; the documented `sys.path` ordering relative to `futu` and `connect` imports; the presence of context cleanup on every context-creating path; suppression of all errors, detected by finding exception handlers whose body consists only of `pass` or `continue`; dead module-level constants, by finding uppercase assignments never read; index coverage, by comparing example directories against the example index; and duplication between the contract tables in `AGENTS.md` and `CONTRIBUTING.md`.

**Why a closed set.** A static tier that grows without bound drifts toward asserting runtime behavior it cannot see. Each property here is decidable from source alone and corresponds to a defect actually observed in this repository.

**Note on error suppression.** The suppression check is AST-based and deterministic. It is what surfaces `examples/67_health_monitor`, where five handlers make every failure unobservable. The check reports sites; whether each site is a genuine defect is reviewed by a human, because suppression is sometimes correct in a monitor loop that must survive a transient error.

### Decision 6: The arity question is resolved by a probe whose result branches the remediation

**Choice.** Add a probe that inspects the installed SDK for the return arity of `get_history_kl_quota()` and `get_warrant()`, preferring runtime observation against a live gateway and falling back to source inspection of the installed package when no gateway is available. The probe reports; it does not fix. Remediation of the four call sites is a separate task that follows the probe and conforms the call sites to whatever was observed.

**Why this is safe to defer.** The specs were written to absorb either answer: `sdk-return-contracts` records both readings and requires the resolution method, so no requirement changes based on the outcome. That is what makes the question deferrable rather than a decision being dodged.

**Fallback when the SDK is absent.** If neither the gateway nor the SDK is available, the probe reports that the question is unresolved and the four call sites remain enumerated as within scope and non-conforming. The state is recorded rather than silently assumed.

### Decision 7: Examples signal failure by exiting non-zero, and may not suppress it

**Choice.** A verification-capable example communicates failure through its exit status. An example that catches an exception must record it and re-raise, or narrow it to a case it genuinely handles.

**Why.** Decision 2 makes exit status authoritative. That only works if examples can actually exit non-zero. Today the harness cannot distinguish a clean run from a fully suppressed one, so this is the enabling change on the example side; without it the live tier's verdicts stay uninformative even with correct classification.

### Decision 8: Validate the RSA key inside `configure_rsa`, before any handshake

**Choice.** Validate that the RSA private key is readable at the point where it is handed to the SDK, and raise a named error if it is not.

`configure_rsa` is the chosen insertion point because it is the single function that already holds the key path and is called on every connection attempt, before any `OpenQuoteContext` is constructed. Validating there catches the problem for every host and every code path without duplicating checks at each call site.

**Why validation is mandatory rather than optional.** The SDK retries a failed handshake internally and indefinitely, so a missing key does not produce an error — it produces a process that never exits. The live tier then reports a timeout, and the operator is left with `check sha error` and no indication that the cause is a filesystem path. Validating first converts an unbounded hang into an immediate, actionable message.

**Alternative considered.** Relying on `connect_opend`'s existing RSA ON/OFF fallback to recover. Rejected: that fallback cannot run, because the first attempt never returns. This was the actual defect observed during the live run.

### Decision 9: Default the single-host configuration to RSA enabled

**Choice.** Make the `FUTU_ADDR` fallback resolve to `is_rsa=True`, matching the two `FUTU_OPEND_HOSTS` branches that already default to `True` when no flag is stated.

**Why.** The same host expressed through the two variables currently gets different RSA settings, which is an internal inconsistency rather than a deliberate distinction. `True` is the correct default because FutuOpenD enables protocol encryption whenever `<rsa_private_key>` is set, which includes local gateways.

**Trade-off accepted.** A gateway genuinely running without RSA now costs one failed handshake before the `RSA ON→OFF` fallback recovers it, since that fallback remains reachable only when the first attempt returns. That cost is small next to the previous behaviour, where the default guaranteed the handshake could not succeed at all. Documented as the `is_rsa=False` escape hatch in `.env.example`.

### Decision 10: Scope handshake-refusal patterns to the timeout path

**Choice.** Restrict `check sha error` and `init connect fail` to reclassifying a *timeout* as `BLOCKED`. Keep the unambiguous refusals — unreachable gateway, login failure, unlock cooldown, missing quote permission — on both the timeout and non-zero-exit paths.

**Why.** These two patterns describe the SDK sitting in its internal retry loop, which is what a timeout is. A process that exited on its own has not demonstrated that, so treating its output as proof that the gateway refused it would mask a genuine defect as external state. This is the one place where an output-derived signal was being allowed to downgrade too eagerly, and narrowing it keeps the asymmetry from Decision 2 intact: output may downgrade a failure, but only where the failure mode it describes is actually evidenced.

**Trade-off accepted.** An example that exits non-zero *only* because of the handshake now reports `FAIL` rather than `BLOCKED`. That is the correct reading — a process that exited has a diagnosable problem — but it will show up as failures if any example does this.

## Risks / Trade-offs

- **The static tier passes while the live tier is failing** → a reader may take green CI as evidence examples work. Mitigation: the two tiers emit visibly distinct verdicts and are never merged into a single pass count; CI names the tier in its check title.

- **The suppression check produces false positives on legitimate monitor loops** → Mitigation: it reports sites for human review rather than failing outright, and the review outcome is recorded per site.

- **Removing `TRADE_EXAMPLES` loses the author's intent that trade examples be skipped when the SIMULATE account is locked** → Mitigation: that intent is now expressed as the BLOCKED outcome in Decision 3, which is enforced rather than merely declared.

- **The probe is inconclusive in environments without the SDK or gateway** → Mitigation: the inconclusive state is recorded explicitly and leaves the call sites flagged, so the question cannot be lost by being skipped.

- **Splitting verification into two tiers doubles the surface a contributor must satisfy** → Mitigation: the static tier is the fast default and the live tier is opt-in, so the common loop stays short.

- **Scope correction on `proposal.md`** — the proposal states this change adds specification only and defers remediation, which contradicts producing design, tasks, and an applicable change. Mitigation: this design treats remediation as in scope; the proposal's scope paragraph needs a corresponding amendment, proposed as part of this change's tasks rather than applied silently.

## Migration Plan

1. Add the static tier and the probe as new checks; leave the existing runner in place.
2. Correct the runner's verdict derivation and outcome model; add the reporting of the not-verified set.
3. Bring the flagged example sites into conformance — error suppression first, since it gates the value of every other verdict.
4. Conform the four arity-dependent call sites to the probe's observation.
5. Remove the superseded `TRADE_EXAMPLES` set and the private-range host defaults.
6. Add the CI workflow running the static tier only.

Rollback: each step is additive until step 2, which changes runner behavior. Steps 1–2 can be reverted by restoring the previous runner. Steps 3–6 are ordinary source changes and revert individually.

## Open Questions

- Whether `black` and `ruff` are intended as enforced gates or advisory. They are configured but not enforced anywhere. If advisory, the static tier reports style as informational; if enforced, style failures fail the tier. Deferred because it changes only the static tier's severity configuration, not the requirements, the two-tier approach, or the task ordering.