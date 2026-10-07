#!/usr/bin/env python3

# Copyright (c) 2026 shing1211
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Live verification tier: run every example against a real OpenD gateway.

This is the LIVE tier. It is the only thing in this repository that can say
whether an example works against OpenD. The static tier
(``scripts/run_static.py``) asserts source properties only, and a green static
run is not evidence about anything at runtime.

Every example needs a reachable gateway. This runner reads its connection
configuration from the environment and never injects a host, key path, or
password of its own -- an earlier version hard-coded a private-range host list
that silently overrode the caller's configured gateway.

Four outcome states, per design.md Decision 3:

    PASS          ran to completion and exited 0
    FAIL          ran and exited non-zero, or errored unexpectedly
    BLOCKED       refused by external state (no gateway, no session, cooldown)
    NOT-VERIFIED  discovered but not run

BLOCKED and NOT-VERIFIED never count as passes. A pass means the example ran
and demonstrated its behavior.

Verdict derivation, per design.md Decision 2: a non-zero exit is a failure,
unconditionally. Inspecting captured output may reclassify a failure as BLOCKED
or as an expected timeout for a declared-unbounded example. It may never
reclassify a failure as a pass. The runner has direct evidence of failure and
only the absence of evidence of success, and those are not equivalent.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples"

TIMEOUT_SEC = 30

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"
NOT_VERIFIED = "NOT-VERIFIED"
UNBOUNDED_EXPECTED = "UNBOUNDED-EXPECTED"

OUTCOMES = (PASS, FAIL, BLOCKED, NOT_VERIFIED)

#: Examples that run until an external limit -- a `while True` loop that exits
#: only on KeyboardInterrupt. For these only, a timeout is the expected outcome.
#: Consulted by the verifier at startup and by classify() on timeout.
#:
#: This set must contain only genuinely unbounded examples. Push examples that
#: merely `sleep(N)` and then exit are *bounded* and belong in SLOW_EXAMPLES --
#: declaring them unbounded would turn a real hang into an expected outcome.
UNBOUNDED_EXAMPLES = frozenset(
    {
        "58_options_greeks",
        "67_health_monitor",
        "71_market_regime",
        "72_candlestick_scanner",
        "73_correlation_tracker",
        "74_orderflow_viz",
        "77_iceberg_detector",
        "81_portfolio_rebalance",
        "87_watchlist_alerts",
        "96_margin_monitor",
    }
)

#: Examples that run for a caller-chosen window via ``--max-minutes``. They are
#: bounded, but their own default window is 5-30 minutes. The verifier asks for
#: a short window instead of raising the ceiling high enough to outlast the
#: default, so they complete and report a real verdict rather than a timeout.
#:
#: name -> minutes requested. There must be a ceiling above this in
#: SLOW_EXAMPLES so the example finishes before the verifier gives up on it.
DURATION_LIMITED_EXAMPLES = {
    "68_trailing_stop": 0.5,
    "69_bollinger_bounce": 0.5,
    "78_grid_trading": 0.5,
    "79_pairs_trading": 0.5,
    "80_multi_leg_options": 0.5,
}

#: Examples that legitimately need longer than TIMEOUT_SEC. These are *bounded*
#: -- each finishes on its own -- so they get a ceiling above their own runtime
#: rather than being declared unbounded. Bounded examples must never be added to
#: UNBOUNDED_EXAMPLES, which would hide a genuine hang.
SLOW_EXAMPLES = {
    "01_snapshot": 600,  # measured 411s: every stock across four markets, batched
    # Examples asked for a short window via --max-minutes still need headroom
    # for connection and setup on top of that window.
    "68_trailing_stop": 90,
    "69_bollinger_bounce": 90,
    "78_grid_trading": 90,
    "79_pairs_trading": 90,
    "80_multi_leg_options": 90,
    # Fixed waits longer than the default ceiling. These are bounded; they
    # simply outlast 30s.
    "05_quote_trade": 60,  # sleep(30) plus connection
    "48_keepalive_handler": 90,  # time.sleep(60) awaiting a heartbeat
    "54_pair_trading": 90,  # time.sleep(60) awaiting 60 candles
    "59_dark_pool_detector": 150,  # DURATION_SEC = 120
    # DURATION_SEC = 300 collection windows.
    "56_order_flow_imbalance": 340,
    "57_vwap_benchmark": 340,
    **{f"{n:03d}_{slug}": 45 for n, slug in (
        (107, "earnings_surprise"), (108, "short_squeeze"), (109, "insider_monitor"),
        (110, "dividend_calendar"), (111, "company_health"), (112, "option_flow"),
        (113, "institutional_flow"), (114, "valuation_heatmap"),
        (115, "option_strategy_builder"), (116, "option_combo_order"),
        (117, "odd_lot_book"), (118, "market_search"), (119, "option_0dte"),
        (120, "option_earnings"), (121, "option_seller"), (122, "fedwatch_macro"),
        (123, "institutional_13f"), (124, "industry_chain"),
        (125, "event_contract_discovery"), (126, "event_contract_live"),
        (127, "prediction_combo"),
    )},
}

#: Output patterns that mean external state refused the run, not that the
#: example is broken. These apply on both the timeout and non-zero-exit paths:
#: each one describes a refusal the gateway is entitled to make, and a process
#: that exited having reported one was still refused.
BLOCKED_PATTERNS = (
    re.compile(r"no reachable opend gateways", re.IGNORECASE),
    re.compile(r"failed to connect to any host", re.IGNORECASE),
    re.compile(r"connection refused", re.IGNORECASE),
    re.compile(r"no event contract quote permission", re.IGNORECASE),
    re.compile(r"quote login failed|trade login failed", re.IGNORECASE),
    # The gateway refuses the trade unlock because too many attempts were
    # made. FutuOpenD answers in English ("too many attempts") or Chinese
    # ("交易密码的尝试次数已达上限"), and both mean the same thing: a
    # time-based cooldown, not a defect in the example.
    re.compile(r"unlock_trade failed: too many attempts", re.IGNORECASE),
    re.compile(r"交易密码的尝试次数已达上限"),
)

#: Patterns that describe the SDK sitting in its own internal handshake retry
#: loop. That loop is precisely what a timeout IS, so these only reclassify a
#: timeout -- never a process that exited on its own. A process that terminated
#: has not demonstrated that the gateway refused it, and treating its output as
#: proof would mask a genuine defect as external state.
BLOCKED_TIMEOUT_ONLY_PATTERNS = (
    re.compile(r"check sha error", re.IGNORECASE),
    re.compile(r"init connect fail", re.IGNORECASE),
)


@dataclass
class Result:
    name: str
    outcome: str
    elapsed: float
    returncode: int
    detail: str = ""
    stderr: str = field(default="", repr=False)


def discover_examples() -> list[str]:
    """The example set, derived from the filesystem (design.md Decision 4).

    This is the only source of the set. There is no hand-maintained roster that
    can drift out of agreement with the repository.
    """
    if not EXAMPLES_DIR.is_dir():
        return []
    return sorted(
        (d.name for d in EXAMPLES_DIR.iterdir() if d.is_dir() and d.name[:1].isdigit()),
        key=_sort_key,
    )


def _sort_key(name: str) -> tuple[int, int, str]:
    digits = ""
    for ch in name:
        if ch.isdigit():
            digits += ch
        else:
            break
    suffix = name[len(digits):]
    number = int(digits) if digits.isdigit() else -1
    return (number, 0 if not suffix else 1, suffix)


def verify_classifications(discovered: set[str]) -> None:
    """Validate the classification sets against the repository and each other.

    A classification naming a nonexistent directory is stale, and a stale
    classification is exactly the failure mode this runner previously had. Two
    sets claiming the same example is a conflict: an example cannot be both
    time-limited and not terminating.
    """
    problems = []
    sets = {
        "UNBOUNDED_EXAMPLES": set(UNBOUNDED_EXAMPLES),
        "SLOW_EXAMPLES": set(SLOW_EXAMPLES),
        "DURATION_LIMITED_EXAMPLES": set(DURATION_LIMITED_EXAMPLES),
    }
    for label, names in sets.items():
        missing = sorted(n for n in names if n not in discovered)
        if missing:
            problems.append(f"{label} names nonexistent example(s): {', '.join(missing)}")

    # An example cannot be both time-limited and not terminating, and asking for
    # a short window is meaningless without a ceiling above it.
    for left, right in (
        ("UNBOUNDED_EXAMPLES", "SLOW_EXAMPLES"),
        ("UNBOUNDED_EXAMPLES", "DURATION_LIMITED_EXAMPLES"),
    ):
        overlap = sorted(sets[left] & sets[right])
        if overlap:
            problems.append(f"{left} and {right} both claim: {', '.join(overlap)}")

    unrealised = sorted(sets["DURATION_LIMITED_EXAMPLES"] - sets["SLOW_EXAMPLES"])
    if unrealised:
        problems.append(
            "DURATION_LIMITED_EXAMPLES asks these examples for a short window but "
            f"SLOW_EXAMPLES gives no ceiling above it: {', '.join(unrealised)}"
        )

    if problems:
        raise SystemExit(
            "classification validation failed:\n  " + "\n  ".join(problems)
        )


def child_env() -> dict[str, str]:
    """Environment for child examples.

    Inherits the caller's configuration unchanged. This runner deliberately
    sets no FUTU_* default: a previous version injected a private-range host
    list and an RSA key path, which overrode a correctly configured .env
    because python-dotenv does not override real environment variables.
    """
    return dict(os.environ)


def timeout_for(name: str) -> int:
    return SLOW_EXAMPLES.get(name, TIMEOUT_SEC)


def looks_blocked(text: str, timed_out: bool = False) -> str | None:
    patterns = BLOCKED_PATTERNS
    if timed_out:
        patterns = patterns + BLOCKED_TIMEOUT_ONLY_PATTERNS
    for pattern in patterns:
        if pattern.search(text or ""):
            return pattern.pattern
    return None


def classify(
    name: str,
    returncode: int,
    stdout: str,
    stderr: str,
    timed_out: bool = False,
) -> tuple[str, str]:
    """Derive (outcome, detail).

    Decision 2: the exit status decides. A non-zero exit is a failure. Output
    inspection runs only over failures, and only to downgrade -- never to
    upgrade. That is why there is no branch here that turns a failure into a
    pass, and why an unrecognised failure stays a failure.
    """
    combined = f"{stdout}\n{stderr}"

    # A clean exit is a pass, unconditionally. Nothing below may reclassify it:
    # an example that succeeded demonstrated its behavior even if the word
    # "failed" appears somewhere in its log output.
    if returncode == 0 and not timed_out:
        return PASS, ""

    # The run did not succeed. Output may now downgrade it, and only downward.
    # A gateway that refuses the handshake keeps the SDK in its internal retry
    # loop, so that refusal shows up as a timeout with the reason in the output;
    # those patterns are therefore consulted only on the timeout path.
    blocked = looks_blocked(combined, timed_out=timed_out)
    if blocked:
        return BLOCKED, f"external state refused the run (matched {blocked})"

    if timed_out:
        if name in UNBOUNDED_EXAMPLES:
            return UNBOUNDED_EXPECTED, f"timeout at {timeout_for(name)}s, expected for unbounded example"
        return FAIL, f"timeout at {timeout_for(name)}s"

    first = _diagnostic_line(stderr)
    return FAIL, f"exit {returncode}: {first[:200]}" if first else f"exit {returncode}"


def _diagnostic_line(stderr: str) -> str:
    """The most informative line of stderr.

    For an uncaught exception the first line is the traceback header, which
    says nothing; the exception itself is the last line. For ordinary output
    the first non-empty line is the right choice.
    """
    lines = [l for l in (stderr or "").splitlines() if l.strip()]
    if not lines:
        return ""
    if any("Traceback (most recent call last)" in l for l in lines):
        return lines[-1].strip()
    return lines[0].strip()


def extra_args_for(name: str) -> list[str]:
    """Arguments the verifier adds for a specific example.

    An example that runs for a caller-chosen window is asked for a short one, so
    it completes and produces a real verdict instead of being killed at the
    ceiling and reported as a timeout.
    """
    minutes = DURATION_LIMITED_EXAMPLES.get(name)
    if minutes is None:
        return []
    return ["--max-minutes", str(minutes)]


def run_example(name: str, env: dict[str, str] | None = None) -> Result:
    """Run one example and classify the result."""
    main_py = EXAMPLES_DIR / name / "main.py"
    started = time.time()
    if not main_py.is_file():
        return Result(name, NOT_VERIFIED, 0.0, -1, detail="no main.py")

    try:
        proc = subprocess.run(
            [sys.executable, str(main_py), *extra_args_for(name)],
            cwd=str(REPO_ROOT),
            env=env or child_env(),
            timeout=timeout_for(name),
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.time() - started
        out = _decode(exc.stdout)
        err = _decode(exc.stderr)
        outcome, detail = classify(name, -1, out, err, timed_out=True)
        return Result(name, outcome, elapsed, -1, detail=detail, stderr=err)
    except OSError as exc:
        elapsed = time.time() - started
        return Result(name, FAIL, elapsed, -1, detail=f"could not launch: {exc}")

    elapsed = time.time() - started
    outcome, detail = classify(name, proc.returncode, proc.stdout, proc.stderr)
    return Result(name, outcome, elapsed, proc.returncode, detail=detail, stderr=proc.stderr)


def _decode(raw) -> str:
    if raw is None:
        return ""
    return raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw


def summarize(results: list[Result], discovered: list[str]) -> dict[str, list[Result]]:
    by_outcome: dict[str, list[Result]] = {o: [] for o in OUTCOMES}
    by_outcome[UNBOUNDED_EXPECTED] = []
    for result in results:
        by_outcome.setdefault(result.outcome, []).append(result)

    ran = {r.name for r in results}
    for name in discovered:
        if name not in ran:
            by_outcome[NOT_VERIFIED].append(
                Result(name, NOT_VERIFIED, 0.0, -1, detail="discovered but not run")
            )
    return by_outcome


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_all.py",
        description="LIVE tier: run examples against a real OpenD gateway.",
    )
    parser.add_argument("--only", help="comma-separated example names to run")
    parser.add_argument(
        "--list", action="store_true", help="list discovered examples and exit"
    )
    args = parser.parse_args(argv)

    discovered = discover_examples()
    verify_classifications(set(discovered))

    rule = "=" * 74
    print(rule)
    print("  Futu Python Samples -- LIVE verification tier")
    print(rule)
    print(f"Repo:      {REPO_ROOT}")
    print(f"Examples:  {len(discovered)} discovered from the filesystem")
    print(f"Timeout:   {TIMEOUT_SEC}s default; unbounded examples {sorted(UNBOUNDED_EXAMPLES)}")
    print()
    print("  Requires a reachable OpenD gateway. A PASS means the example ran and")
    print("  demonstrated its behavior; BLOCKED and NOT-VERIFIED are not passes.")
    print("  This is the LIVE tier. For source properties use scripts/run_static.py.")
    print(f"{rule}\n")

    if args.list:
        for name in discovered:
            print(name)
        return 0

    selected = discovered
    if args.only:
        wanted = {s.strip() for s in args.only.split(",") if s.strip()}
        selected = [n for n in discovered if n in wanted]

    env = child_env()
    results: list[Result] = []
    for name in selected:
        print(f"  {name}: ", end="", flush=True)
        result = run_example(name, env)
        results.append(result)
        suffix = f" - {result.detail}" if result.detail else ""
        print(f"{result.outcome} ({result.elapsed:.1f}s){suffix}", flush=True)

    # Account against what this invocation intended to run. A --only run did not
    # decline to verify the rest, so the others are neither passed nor
    # not-verified here; a full run accounts against every discovered directory.
    by_outcome = summarize(results, selected)
    partial = bool(args.only)

    print(f"\n{rule}\n  LIVE tier summary\n{rule}")
    for outcome in (*OUTCOMES, UNBOUNDED_EXPECTED):
        bucket = by_outcome.get(outcome, [])
        if not bucket:
            continue
        print(f"\n{outcome} ({len(bucket)}):")
        for result in bucket:
            print(f"  {result.name}")

    passes = len(by_outcome[PASS])
    blocking_failures = len(by_outcome[FAIL])
    print(f"\nTotal examples discovered: {len(discovered)}")
    print(f"  passed:            {passes}")
    print(f"  failed:            {blocking_failures}")
    print(f"  blocked:           {len(by_outcome[BLOCKED])}")
    print(f"  not verified:      {len(by_outcome[NOT_VERIFIED])}")
    if by_outcome.get(UNBOUNDED_EXPECTED):
        print(f"  unbounded expected:{len(by_outcome[UNBOUNDED_EXPECTED])}")

    unaccounted = len(selected) - sum(
        len(by_outcome[o])
        for o in (*OUTCOMES, UNBOUNDED_EXPECTED)
        if o in by_outcome
    )
    if unaccounted:
        print(f"\nWARNING: {unaccounted} example(s) unaccounted for.")

    print("\nLIVE tier only. Source properties are covered by scripts/run_static.py.\n")

    verified = passes + len(by_outcome[UNBOUNDED_EXPECTED])
    if partial:
        print(
            f"Partial run: {verified}/{len(selected)} selected example(s) verified "
            f"against a live gateway ({len(discovered)} discovered in total)."
        )
    elif verified == len(discovered):
        print("All examples verified against a live gateway.")
    else:
        print("Not every example passed; see the state breakdown above.")
    return 1 if (blocking_failures or unaccounted) else 0


if __name__ == "__main__":
    sys.exit(main())