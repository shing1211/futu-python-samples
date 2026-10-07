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

"""Static verification tier CLI.

Runs the gateway-free checks in ``scripts/static_checks`` and reports findings.

This is a separate verdict channel from ``scripts/run_all.py``. It asserts
nothing about runtime behavior: a clean static run does NOT mean the examples
work against OpenD. The banner below is deliberately explicit about that so a
green result cannot be misread as a live-tier pass.

Exit status is 0 when no finding has a blocking severity, 1 when at least one
does, and 2 on a usage error.

Style is opt-in via --style and is not part of the correctness check set; see
design.md Decision 5.
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import static_checks
from static_checks.core import (
    REPO_ROOT,
    SEVERITY_FAIL,
    SEVERITY_INFO,
    SEVERITY_REPORT,
    blocking,
    load_all,
    names,
    run_checks,
)

TIER = "STATIC"
LIVE_TIER = "scripts/run_all.py"


def _banner(root: pathlib.Path, examples: int) -> str:
    rule = "=" * 74
    return "\n".join(
        [
            rule,
            f"  Futu Python Samples -- {TIER} verification tier",
            rule,
            f"Root:     {root}",
            f"Examples: {examples} discovered from the filesystem",
            "",
            "  This tier asserts source properties only. A clean run does NOT",
            f"  mean the examples work against OpenD -- the live tier ({LIVE_TIER})",
            "  is what establishes that, and it needs a reachable gateway.",
            rule,
            "",
        ]
    )


def _style_findings(root: pathlib.Path, severity: str) -> list:
    """Optional ruff/black integration.

    Skipped silently when the tools are absent, so the tier stays runnable on a
    bare standard library. Findings carry the configured severity, which is how
    the gate-versus-advisory decision (tasks.md 6.2) becomes observable.
    """
    findings = []
    # ruff keeps --quiet; black 26 dropped it, so the flag sets differ per tool.
    for tool, extra in (
        ("ruff", ["check", "--quiet"]),
        ("black", ["--check"]),
    ):
        exe = _which(tool)
        if exe is None:
            continue
        try:
            proc = subprocess.run(
                [exe, *extra, str(root)],
                cwd=str(root),
                capture_output=True,
                text=True,
            )
        except OSError:
            continue
        if proc.returncode == 0:
            continue
        detail = [
            line
            for line in (proc.stdout or proc.stderr or "").splitlines()
            if line.strip()
        ]
        # Tool usage errors are not style findings; report them as such so a
        # misconfigured invocation cannot masquerade as a clean style result.
        usage_error = any("Usage:" in line for line in detail[:3])
        findings.append(
            static_checks.Finding(
                check=f"style-{tool}",
                path=str(root),
                message=(
                    f"{tool} could not run: {detail[0][:160]}"
                    if usage_error
                    else f"{tool} reported findings ({len(detail)} line(s)); first: {detail[0][:160]}"
                ),
                severity=severity,
            )
        )
    return findings


def _which(tool: str) -> str | None:
    import shutil

    return shutil.which(tool)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_static.py",
        description=(
            "Gateway-free static checks. Does not verify runtime behavior; "
            f"use {LIVE_TIER} for that."
        ),
    )
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=REPO_ROOT,
        help="repository root to inspect (default: the repository this script lives in)",
    )
    parser.add_argument(
        "--checks",
        help="comma-separated check names to run (default: all)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list registered check names and exit",
    )
    parser.add_argument(
        "--style",
        action="store_true",
        help="also run ruff and black if installed (not part of the correctness set)",
    )
    parser.add_argument(
        "--style-severity",
        choices=[SEVERITY_INFO, SEVERITY_REPORT, SEVERITY_FAIL],
        default=SEVERITY_INFO,
        help="severity assigned to style findings when --style is given (default: info)",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    load_all()

    if args.list:
        for name in names():
            print(name)
        return 0

    selected = None
    if args.checks:
        selected = [s.strip() for s in args.checks.split(",") if s.strip()]
        unknown = [s for s in selected if s not in names()]
        if unknown:
            print(
                f"error: unknown check(s): {', '.join(unknown)}", file=sys.stderr
            )
            print(f"available: {', '.join(names())}", file=sys.stderr)
            return 2

    ctx = static_checks.context_for(root)
    print(_banner(root, len(ctx.example_dirs)))

    findings = run_checks(ctx, selected)
    if args.style:
        findings.extend(_style_findings(root, args.style_severity))

    order = {SEVERITY_FAIL: 0, SEVERITY_REPORT: 1, SEVERITY_INFO: 2}
    findings.sort(key=lambda f: (order.get(f.severity, 3), f.check, f.path, f.line or 0))

    if not findings:
        print(f"{TIER} tier: no findings.")
        print(f"{TIER} tier says nothing about runtime behavior.\n")
        return 0

    for finding in findings:
        print(finding)

    hard = blocking(findings)
    by_severity: dict[str, int] = {}
    for finding in findings:
        by_severity[finding.severity] = by_severity.get(finding.severity, 0) + 1

    print(f"\n{TIER} tier summary: {len(findings)} finding(s)")
    for severity in (SEVERITY_FAIL, SEVERITY_REPORT, SEVERITY_INFO):
        if severity in by_severity:
            print(f"  {severity:<7} {by_severity[severity]}")
    print(f"\n{TIER} tier asserts source properties only; it does not establish")
    print(f"that the examples work against OpenD. Use {LIVE_TIER} for that.\n")

    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())