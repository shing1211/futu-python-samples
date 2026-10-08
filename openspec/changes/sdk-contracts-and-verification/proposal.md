# Proposal

## Why

This repository documents several hard-won contracts about the Futu OpenAPI SDK — return shapes that differ from the official docs, enums that do not exist, and pandas access patterns that raise — but it has no way to check that those contracts are still true. The two documents that carry them (`AGENTS.md` and `CONTRIBUTING.md`) duplicate the same tables with a manual obligation to keep both in sync, and `requirements.txt` pins only a floor (`futu-api>=10.9.6908`), so the contracts can drift out of date on any install without any signal.

The consequence is already visible. `CONTRIBUTING.md` and `AGENTS.md` both state that `get_history_kl_quota()` returns a 3-tuple with no leading `ret` code, yet four call sites (`examples/26_history_kl_quota`, `examples/28_warrant`, `examples/64_backtesting`, `examples/67_health_monitor`) unpack a `ret` from it. Both readings cannot be correct, and nothing in the repository can currently distinguish them.

Meanwhile the only verification mechanism, `scripts/run_all.py`, cannot detect the disagreement. It classifies a non-zero exit as PASS unless stderr contains one of a fixed set of substrings (`traceback`, `error`, `exception`, `failed`, …), and it captures stdout without ever inspecting it. A run that crashes with empty stderr is reported as PASS. Because `example-verification` cannot currently establish what a correct run looks like, `sdk-return-contracts` cannot be verified against it.

We are specifying these two capabilities together, in this order, because the first defines what must be true and the second defines what counts as evidence that it is true.

## What Changes

- Introduce a `sdk-return-contracts` capability that records the SDK's non-obvious return shapes, dead enums, and pandas access rules as explicit requirements, each carrying the provenance and confidence of its evidence.
- Require that any return shape which cannot be confirmed by direct observation against a live gateway be recorded as unverified rather than asserted, so the specification cannot codify a guess.
- Require that call sites relying on a contradicted return shape be brought into scope explicitly, so an unresolved discrepancy is visible instead of silently blessed.
- Introduce an `example-verification` capability defining the observable contract of the example runner: what a pass is, what a failure is, and which outcomes must never be reported as a pass.
- Require the runner to derive its verdict from process exit status and captured output rather than from substring matching, and declare any heuristic it retains as non-authoritative.
- Require that examples which cannot signal failure are identified as a defect in those examples, not excused by the runner.

No change is made to the Futu SDK integration or the connection layer's behavior. This change both specifies the two capabilities and remediates the defects they describe, because a specification nothing enforces reproduces the problem it documents: the remediation is what makes the requirements checkable. Specifically it reworks the live tier's verdict derivation, adds the gateway-free static tier, brings the flagged example sites into conformance, and adds the probe that settles the return-arity question.

Out of scope, and deferred to a follow-up change: reconciling `AGENTS.md` and `CONTRIBUTING.md` against the new spec artifact, and fixing the licensing defects found during review.

## Capabilities

### New Capabilities

- `sdk-return-contracts`: The authoritative record of Futu OpenAPI SDK interfaces that deviate from official documentation — return arity and shape, enum names that do not exist, and DataFrame access patterns that raise — including the evidence status of each claim and the obligations on call sites that depend on them.
- `example-verification`: The observable contract of the example verification harness — how a verdict is derived, which outcomes must never be reported as a pass, and the requirement that verification be capable of failing.
- `gateway-connection`: How OpenD connection settings are resolved and validated — RSA key configuration, single-host versus host-list parsing, and the requirement that a misconfiguration fail fast rather than hang.

### Modified Capabilities

None. The project has no existing specs (`openspec list --specs` is empty), so no established capability's requirements change.

## Impact

- **Affected code (specification targets and remediation):** `scripts/run_all.py` is reworked under `example-verification`; a new `scripts/run_static.py` and `scripts/probe_return_arity.py` implement the static tier and the probe; `examples/connect.py` is unchanged; the four call sites named above were investigated and found already conforming.
- **Affected documentation:** `AGENTS.md` is unchanged. `CONTRIBUTING.md` gains sections describing both verification tiers, the four outcome states, the gateway-free scope boundary, and how to suppress an error legitimately. Its contract tables are deliberately left untouched; both prose tables remain the practical source until the duplication is retired.
- **Dependencies:** the static tier adds none — it is standard library only and needs no SDK and no gateway. The live tier needs the existing runtime dependencies plus a reachable OpenD gateway.
- **Resolved question:** whether `get_history_kl_quota()` and `get_warrant()` return a leading `ret` code. The probe observed both at the minimum supported version (`10.9.6908`) and at `10.11.7108`: each returns a 2-tuple comprising a leading status code and a nested 3-tuple. The four call sites conform; the prose tables describe only the nested value and are the incorrect record. See `specs/sdk-return-contracts/observations.md`.