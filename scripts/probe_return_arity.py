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

"""Probe the return arity of SDK interfaces that differ from the docs.

The prose tables in AGENTS.md and CONTRIBUTING.md described
``get_history_kl_quota()`` and ``get_warrant()`` as returning a 3-tuple with no
leading status code, while every call site unpacks a leading ``ret``. Both
readings cannot be right, and nothing in the repository could tell them apart.

This probe settles it by observation. It REPORTS and never fixes: conforming a
call site is a separate, deliberate step, because the answer determines what
"conforming" means.

Evidence is tried strongest-first:

  live      call the method against a real OpenD gateway and count the result
  source    read the installed package's source and read its return statements
  unresolved  neither was available; the question stays open

Usage:

    python3 scripts/probe_return_arity.py
    python3 scripts/probe_return_arity.py --source   # skip the gateway
    python3 scripts/probe_return_arity.py --json
"""

from __future__ import annotations

import argparse
import inspect
import json
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "examples"))

TARGETS = (
    # The two the original specification opened this change to settle.
    "get_history_kl_quota",
    "get_warrant",
    # Found by the first full live run: these return more values than a plain
    # (ret, data) pair, and every call site unpacked too few.
    "get_broker_queue",
    "get_economic_calendar",
    "get_institution_list",
    # Confirmed deviating and already handled correctly by its call site.
    "request_history_kline",
    "get_order_book",
)

EVIDENCE_LIVE = "live"
EVIDENCE_SOURCE = "source"
EVIDENCE_UNRESOLVED = "unresolved"


def sdk_version() -> str | None:
    try:
        import futu
    except ImportError:
        return None
    return getattr(futu, "version", None) or getattr(futu, "__version__", None)


def _arity_of(value) -> int | None:
    if isinstance(value, tuple):
        return len(value)
    return None


def probe_live(name: str) -> dict | None:
    """Call the method against a real gateway and observe the result."""
    try:
        from connect import create_quote_context
    except Exception as exc:  # import-time failure is itself a result
        return {"error": f"cannot import connect: {type(exc).__name__}: {exc}"}
    try:
        ctx = create_quote_context()
    except Exception as exc:
        return {"error": f"cannot reach gateway: {type(exc).__name__}: {exc}"}
    try:
        method = getattr(ctx, name, None)
        if method is None:
            return {"error": f"{name} is not present on the quote context"}
        result = method()
        arity = _arity_of(result)
        if arity is None:
            return {
                "error": f"{name} returned {type(result).__name__}, not a tuple",
                "value": repr(result)[:200],
            }
        detail = {
            "outer_arity": arity,
            "has_leading_status_code": isinstance(result[0], int),
        }
        if arity >= 2 and isinstance(result[1], tuple):
            detail["inner_arity"] = len(result[1])
            detail["inner_types"] = [type(x).__name__ for x in result[1]]
        return detail
    except Exception as exc:
        return {"error": f"{name} raised {type(exc).__name__}: {exc}"}
    finally:
        try:
            ctx.close()
        except Exception:
            pass


def probe_source(name: str) -> dict | None:
    """Read the installed package's source for this method's return statements."""
    try:
        from futu import OpenQuoteContext
    except ImportError:
        return None
    method = getattr(OpenQuoteContext, name, None)
    if method is None:
        return {"error": f"{name} is not present on OpenQuoteContext"}
    try:
        src = inspect.getsource(method)
    except (OSError, TypeError) as exc:
        return {"error": f"cannot read source for {name}: {exc}"}

    returns = [
        line.strip()
        for line in src.splitlines()
        if re.match(r"^\s*return\b", line)
    ]
    success = [r for r in returns if "RET_ERROR" not in r and "msg" not in r]
    outer = None
    inner = None
    if success:
        head = success[-1]
        match = re.match(r"^return\s+(.+)$", head)
        expr = match.group(1) if match else ""
        outer = _arity_of_literal(expr)
        inner_match = re.search(r"\(([^()]*)\)\s*$", expr)
        if inner_match and expr.rstrip().endswith(")"):
            inner = len([p for p in inner_match.group(1).split(",") if p.strip()])
    return {
        "return_statements": returns,
        "outer_arity": outer,
        "inner_arity": inner,
        "has_leading_status_code": bool(success and re.match(r"^return\s+\w+,", success[-1])),
    }


def _arity_of_literal(expr: str) -> int | None:
    """Count top-level comma-separated items in a return expression.

    Handles both parenthesized ``(a, b)`` and the bare ``a, b`` form that Python
    uses for a returned tuple, and does not split commas nested inside a call or
    a subscript.
    """
    expr = expr.strip()
    if expr.startswith("(") and expr.endswith(")"):
        inner = expr[1:-1]
    else:
        inner = expr
    items = 0
    current = ""
    depth = 0
    for ch in inner:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            items += 1
        else:
            current += ch
    if current.strip() or items:
        return items + 1
    return 0


def probe(name: str, prefer_source_only: bool = False) -> dict:
    result: dict = {"method": name, "evidence": EVIDENCE_UNRESOLVED}

    if not prefer_source_only:
        live = probe_live(name)
        if live and "error" not in live:
            result["evidence"] = EVIDENCE_LIVE
            result["observation"] = live
            return result
        result["live_attempt"] = live

    source = probe_source(name)
    if source and "error" not in source:
        result["evidence"] = EVIDENCE_SOURCE
        result["observation"] = source
        return result
    if source:
        result["source_attempt"] = source
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="probe_return_arity.py",
        description=(
            "Report the return arity of SDK interfaces that differ from the docs. "
            "Reports only; changes no code."
        ),
    )
    parser.add_argument(
        "--source",
        action="store_true",
        help="skip the gateway and read the installed package source only",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)

    version = sdk_version()
    results = [probe(name, prefer_source_only=args.source) for name in TARGETS]
    payload = {"sdk_version": version, "results": results}

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0 if all(r["evidence"] != EVIDENCE_UNRESOLVED for r in results) else 1

    rule = "=" * 74
    print(rule)
    print("  Return-arity probe -- reports only, changes no code")
    print(rule)
    print(f"SDK version: {version or 'not importable'}")
    print()

    unresolved = False
    for result in results:
        evidence = result["evidence"]
        print(f"{result['method']}:")
        print(f"  evidence: {evidence}")
        if evidence == EVIDENCE_UNRESOLVED:
            unresolved = True
            for key in ("live_attempt", "source_attempt"):
                if key in result:
                    print(f"  {key}: {result[key].get('error', result[key])}")
            print("  => question remains open; the call sites stay in scope\n")
            continue
        obs = result["observation"]
        if "outer_arity" in obs:
            print(f"  outer arity: {obs['outer_arity']}")
        if obs.get("inner_arity") is not None:
            print(f"  inner arity: {obs['inner_arity']}")
        print(f"  leading status code: {obs.get('has_leading_status_code')}")
        if obs.get("inner_types"):
            print(f"  inner types: {obs['inner_types']}")
        for stmt in obs.get("return_statements", []):
            print(f"    {stmt}")
        print()

    if unresolved:
        print("At least one interface could not be observed. Recorded as unresolved.")
    else:
        print("All targets observed. Record the result in specs/sdk-return-contracts/spec.md.")
    return 1 if unresolved else 0


if __name__ == "__main__":
    sys.exit(main())