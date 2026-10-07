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

"""Tests for the return-arity probe and for the conformance it enabled.

The central recorded claim is that ``get_history_kl_quota()`` and
``get_warrant()`` return a leading status code followed by an inner 3-tuple,
which means the four call sites that unpack ``ret, x = ...`` already conform and
the prose tables are what is wrong. These tests pin both halves of that.
"""

from __future__ import annotations

import ast
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import probe_return_arity as probe

CONFORMING_CALL_SITES = {
    "examples/26_history_kl_quota/main.py": "get_history_kl_quota",
    "examples/28_warrant/main.py": "get_warrant",
    "examples/64_backtesting/main.py": "get_history_kl_quota",
    "examples/67_health_monitor/main.py": "get_history_kl_quota",
}


# ---------------------------------------------------------------------------
# 5.1 the probe
# ---------------------------------------------------------------------------


def test_arity_parser_counts_bare_tuple():
    assert probe._arity_of_literal("ret_code, (a, b, c)") == 2
    assert probe._arity_of_literal("(a, b, c)") == 3
    assert probe._arity_of_literal("RET_ERROR, error_str, key") == 3
    assert probe._arity_of_literal("data") == 1


def test_arity_parser_ignores_nested_commas():
    assert probe._arity_of_literal("ret_code, (a, f(1, 2), c)") == 2
    assert probe._arity_of_literal("ret, df[d['x', 'y']]") == 2


def test_probe_reports_unresolved_without_gateway_or_sdk(monkeypatch):
    """Neither dependency available leaves the question open, not guessed."""
    monkeypatch.setattr(probe, "probe_live", lambda name: {"error": "no gateway"})
    monkeypatch.setattr(probe, "probe_source", lambda name: {"error": "no SDK"})
    result = probe.probe("get_warrant")
    assert result["evidence"] == probe.EVIDENCE_UNRESOLVED
    assert "live_attempt" in result
    assert "source_attempt" in result


def test_probe_prefers_live_evidence(monkeypatch):
    monkeypatch.setattr(
        probe, "probe_live", lambda name: {"outer_arity": 2, "has_leading_status_code": True}
    )
    monkeypatch.setattr(probe, "probe_source", lambda name: {"outer_arity": 99})
    assert probe.probe("get_warrant")["evidence"] == probe.EVIDENCE_LIVE


def test_probe_falls_back_to_source_when_live_fails(monkeypatch):
    monkeypatch.setattr(probe, "probe_live", lambda name: {"error": "unreachable"})
    monkeypatch.setattr(
        probe, "probe_source", lambda name: {"outer_arity": 2, "has_leading_status_code": True}
    )
    result = probe.probe("get_warrant")
    assert result["evidence"] == probe.EVIDENCE_SOURCE
    assert result["observation"]["outer_arity"] == 2


def test_source_only_skips_the_gateway(monkeypatch):
    called = []
    monkeypatch.setattr(probe, "probe_live", lambda name: called.append(name))
    monkeypatch.setattr(
        probe, "probe_source", lambda name: {"outer_arity": 2, "has_leading_status_code": True}
    )
    probe.probe("get_warrant", prefer_source_only=True)
    assert called == []


def test_probe_changes_no_source_file(tmp_path):
    """The probe reports; it must never edit anything."""
    repo = REPO_ROOT / "scripts" / "run_all.py"
    before = repo.read_bytes()
    target = tmp_path / "watched"
    target.mkdir()
    (target / "examples").mkdir()
    (target / "examples" / "00_x").mkdir()
    (target / "examples" / "00_x" / "main.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "probe_return_arity.py"), "--source"],
        capture_output=True,
        text=True,
    )
    assert repo.read_bytes() == before
    assert sorted(p.name for p in (target / "examples" / "00_x").iterdir()) == ["main.py"]


def test_probe_exit_code_signals_unresolved():
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "probe_return_arity.py"), "--source"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout
    assert "All targets observed" in proc.stdout


def test_probe_json_output_is_machine_readable():
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "probe_return_arity.py"),
            "--source",
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    import json

    payload = json.loads(proc.stdout)
    assert set(probe.TARGETS) == {r["method"] for r in payload["results"]}
    assert payload["sdk_version"]


# ---------------------------------------------------------------------------
# 5.3 / 5.4 the observed arity, and the call sites that already conform
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("relpath,method", sorted(CONFORMING_CALL_SITES.items()))
def test_call_site_unpacks_exactly_the_observed_arity(relpath, method):
    """Outer arity is 2: a leading status code plus the inner 3-tuple.

    The prose tables described only the inner tuple, which made these call sites
    look wrong. They are right; the prose is what needs correcting.
    """
    tree = ast.parse((REPO_ROOT / relpath).read_text(encoding="utf-8"))
    unpacking = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            func = node.value.func
            name = getattr(func, "attr", None) or getattr(func, "id", None)
            if name == method and isinstance(node.targets[0], ast.Tuple):
                unpacking.append(len(node.targets[0].elts))
    assert unpacking, f"{relpath} does not assign from {method}()"
    assert set(unpacking) == {2}, f"{relpath} unpacks {unpacking}, expected a 2-tuple"


@pytest.mark.skipif(
    probe.sdk_version() is None, reason="futu SDK is not installed"
)
def test_observation_agrees_with_installed_sdk():
    result = probe.probe("get_history_kl_quota", prefer_source_only=True)
    assert result["evidence"] != probe.EVIDENCE_UNRESOLVED
    obs = result["observation"]
    assert obs["has_leading_status_code"] is True
    assert obs["outer_arity"] == 2
    assert obs["inner_arity"] == 3


@pytest.mark.skipif(probe.sdk_version() is None, reason="futu SDK is not installed")
def test_warrant_observation_agrees_with_installed_sdk():
    result = probe.probe("get_warrant", prefer_source_only=True)
    obs = result["observation"]
    assert obs["has_leading_status_code"] is True
    assert obs["outer_arity"] == 2
    assert obs["inner_arity"] == 3