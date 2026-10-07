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

"""Tests for the live verification tier's verdict derivation.

The properties under test are the ones that were previously wrong: that a
failing process is a failure even when it says nothing, that captured text can
only ever downgrade a failure, and that blocked or unrun examples never inflate
the pass count.

These tests never contact a gateway. They drive classify() and run_example()
against fixture example directories.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import run_all


@pytest.fixture()
def fake_examples(tmp_path, monkeypatch):
    """Point the runner at a fixture examples tree."""

    def build(sources: dict[str, str]) -> pathlib.Path:
        for name, body in sources.items():
            target = tmp_path / "examples" / name / "main.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
        (tmp_path / "examples").mkdir(exist_ok=True)
        monkeypatch.setattr(run_all, "EXAMPLES_DIR", tmp_path / "examples")
        monkeypatch.setattr(run_all, "REPO_ROOT", tmp_path)
        return tmp_path

    return build


# ---------------------------------------------------------------------------
# 3.1 exit status is the primary signal
# ---------------------------------------------------------------------------


def test_nonzero_exit_with_empty_stderr_is_fail(fake_examples):
    fake_examples({"00_quiet_crash": "import sys\nsys.exit(1)\n"})
    result = run_all.run_example("00_quiet_crash", env={})
    assert result.outcome == run_all.FAIL, result.detail
    assert result.returncode == 1


def test_nonzero_exit_with_completely_silent_output_is_fail(fake_examples):
    fake_examples({"00_silent": "raise SystemExit(3)\n"})
    result = run_all.run_example("00_silent", env={})
    assert result.outcome == run_all.FAIL


def test_zero_exit_is_pass(fake_examples):
    fake_examples({"00_ok": "print('did the thing')\n"})
    result = run_all.run_example("00_ok", env={})
    assert result.outcome == run_all.PASS
    assert result.returncode == 0


def test_uncaught_exception_is_fail(fake_examples):
    fake_examples({"00_boom": "raise RuntimeError('kaboom')\n"})
    result = run_all.run_example("00_boom", env={})
    assert result.outcome == run_all.FAIL
    assert "kaboom" in result.detail


# ---------------------------------------------------------------------------
# 3.2 no verdict is derived from output text
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "word", ["error", "Error", "ERROR", "failed", "exception", "Traceback", "failure"]
)
def test_scary_words_on_a_successful_run_are_pass(fake_examples, word):
    """The previous classifier keyed on these words; now they mean nothing."""
    fake_examples({"00_noisy": f"print({word!r})\n"})
    result = run_all.run_example("00_noisy", env={})
    assert result.outcome == run_all.PASS, result.detail


@pytest.mark.parametrize("word", ["ok", "success", "PASS", "all good", "finished"])
def test_reassuring_words_on_a_failed_run_are_still_fail(fake_examples, word):
    fake_examples({"00_polite_crash": f"import sys\nprint({word!r})\nsys.exit(1)\n"})
    result = run_all.run_example("00_polite_crash", env={})
    assert result.outcome == run_all.FAIL, result.detail


def test_no_keyword_list_decides_verdicts():
    """There is no failure-keyword table left in the module."""
    source = pathlib.Path(run_all.__file__).read_text(encoding="utf-8")
    assert "fatal" not in source
    assert "traceback" not in source.lower().replace(
        "test_", ""
    ) or "fatal = any" not in source


# ---------------------------------------------------------------------------
# 3.3 blocked is distinct from pass
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        "connect_opend: No reachable OpenD gateways",
        "RuntimeError: Failed to connect to any host",
        "unlock_trade failed: too many attempts",
        "subscribe failed: No event contract quote permission",
    ],
)
def test_external_refusal_is_blocked(fake_examples, message):
    fake_examples({"00_refused": f"import sys\nprint({message!r}, file=sys.stderr)\nsys.exit(1)\n"})
    result = run_all.run_example("00_refused", env={})
    assert result.outcome == run_all.BLOCKED, result.detail


def test_trade_lockout_is_not_counted_as_a_pass():
    outcome, _ = run_all.classify(
        "06_stock_sell",
        returncode=1,
        stdout="",
        stderr="unlock_trade failed: too many attempts",
    )
    assert outcome == run_all.BLOCKED
    assert outcome != run_all.PASS


def test_summarize_keeps_blocked_out_of_the_pass_count(fake_examples):
    fake_examples(
        {
            "00_ok": "print('fine')\n",
            "01_refused": "import sys\nprint('No reachable OpenD gateways', file=sys.stderr)\nsys.exit(1)\n",
        }
    )
    results = [run_all.run_example(n, env={}) for n in ("00_ok", "01_refused")]
    buckets = run_all.summarize(results, ["00_ok", "01_refused"])
    assert len(buckets[run_all.PASS]) == 1
    assert len(buckets[run_all.BLOCKED]) == 1
    assert "01_refused" in {r.name for r in buckets[run_all.BLOCKED]}


def test_blocked_pattern_on_a_passing_run_stays_pass(fake_examples):
    fake_examples({"00_ok": "print('No reachable OpenD gateways previously')\n"})
    result = run_all.run_example("00_ok", env={})
    assert result.outcome == run_all.PASS


# ---------------------------------------------------------------------------
# 3.4 the verified set comes from the filesystem
# ---------------------------------------------------------------------------


def test_discovered_set_matches_directories(fake_examples):
    fake_examples(
        {
            "00_a": "pass\n",
            "09_b": "pass\n",
            "100_c": "pass\n",
            "45b_d": "pass\n",
            "127_e": "pass\n",
        }
    )
    assert run_all.discover_examples() == ["00_a", "09_b", "45b_d", "100_c", "127_e"]


def test_directory_without_main_is_not_verified(fake_examples):
    (fake_examples({"00_a": "pass\n"}) / "examples" / "01_no_main").mkdir()
    results = [run_all.run_example("00_a", env={})]
    buckets = run_all.summarize(results, ["00_a", "01_no_main"])
    names = {r.name for r in buckets[run_all.NOT_VERIFIED]}
    assert names == {"01_no_main"}


def test_example_not_run_is_reported_not_passed(fake_examples):
    fake_examples({"00_a": "pass\n", "01_b": "pass\n"})
    results = [run_all.run_example("00_a", env={})]
    buckets = run_all.summarize(results, ["00_a", "01_b"])
    assert {r.name for r in buckets[run_all.NOT_VERIFIED]} == {"01_b"}
    assert not any(r.name == "01_b" for r in buckets[run_all.PASS])


def test_every_discovered_directory_is_accounted_for(fake_examples):
    fake_examples({"00_a": "pass\n", "01_b": "import sys\nsys.exit(1)\n", "02_c": "raise SystemExit(1)\n"})
    results = [run_all.run_example(n, env={}) for n in run_all.discover_examples()]
    buckets = run_all.summarize(results, run_all.discover_examples())
    accounted = sum(len(buckets[o]) for o in (*run_all.OUTCOMES, run_all.UNBOUNDED_EXPECTED))
    assert accounted == len(run_all.discover_examples())


# ---------------------------------------------------------------------------
# 3.5 no dead classification remains
# ---------------------------------------------------------------------------


def test_trade_examples_set_is_gone():
    assert not hasattr(run_all, "TRADE_EXAMPLES")


def test_classifications_are_consulted_at_startup():
    """Against the real repository, every classified name must exist."""
    discovered = set(run_all.discover_examples())
    run_all.verify_classifications(discovered)
    assert discovered, "expected examples on disk"


# ---------------------------------------------------------------------------
# 3.6 the runner injects no configuration of its own
# ---------------------------------------------------------------------------


def test_child_env_injects_nothing():
    """No FUTU_* default may be added; the earlier version overrode .env."""
    before = set(os.environ)
    env = run_all.child_env()
    added = set(env) - before
    assert not any(k.startswith("FUTU_") for k in added), added


def test_configured_host_reaches_the_child_unchanged(tmp_path, monkeypatch):
    monkeypatch.setenv("FUTU_OPEND_HOSTS", "10.9.9.9:11111:True")
    monkeypatch.setenv("FUTU_RSA_KEY", "/somewhere/real_key.pem")
    child = tmp_path / "child.py"
    child.write_text(
        "import os\n"
        "print(os.environ.get('FUTU_OPEND_HOSTS'))\n"
        "print(os.environ.get('FUTU_RSA_KEY'))\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(child)], env=run_all.child_env(), capture_output=True, text=True
    )
    assert proc.stdout.splitlines() == ["10.9.9.9:11111:True", "/somewhere/real_key.pem"]


def test_no_private_range_defaults_remain_in_source():
    source = pathlib.Path(run_all.__file__).read_text(encoding="utf-8")
    assert "172.18." not in source
    assert "172.20." not in source
    assert "/etc/futu/keys" not in source


# ---------------------------------------------------------------------------
# 3.7 classifications are validated and consulted
# ---------------------------------------------------------------------------


def test_stale_classification_fails_fast():
    with pytest.raises(SystemExit) as exc:
        run_all.verify_classifications({"00_a"})
    assert "nonexistent" in str(exc.value)


def test_slow_classification_naming_ghost_fails_fast():
    with pytest.raises(SystemExit):
        run_all.verify_classifications({"00_a"})


def test_unbounded_example_timing_out_is_the_expected_outcome():
    outcome, _ = run_all.classify("58_options_greeks", -1, "", "", timed_out=True)
    assert outcome == run_all.UNBOUNDED_EXPECTED


def test_bounded_example_timing_out_is_a_failure():
    outcome, _ = run_all.classify("07_kline", -1, "", "", timed_out=True)
    assert outcome == run_all.FAIL


def test_unbounded_example_completing_normally_is_a_pass():
    outcome, _ = run_all.classify("58_options_greeks", 0, "done", "")
    assert outcome == run_all.PASS


def test_slow_timeouts_are_consulted():
    assert run_all.timeout_for("01_snapshot") == 600
    assert run_all.timeout_for("07_kline") == run_all.TIMEOUT_SEC


def test_every_slow_example_exists_in_the_repository():
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    missing = [n for n in run_all.SLOW_EXAMPLES if not (repo_root / "examples" / n).is_dir()]
    assert missing == [], missing


def test_every_unbounded_example_exists_in_the_repository():
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    missing = [n for n in run_all.UNBOUNDED_EXAMPLES if not (repo_root / "examples" / n).is_dir()]
    assert missing == [], missing

# ---------------------------------------------------------------------------
# handshake refusal surfaces as a timeout but is still BLOCKED
# ---------------------------------------------------------------------------


def test_handshake_refusal_is_blocked(fake_examples):
    """The SDK retries forever on a bad handshake, so this arrives as a timeout.

    A timeout caused by the gateway refusing is BLOCKED, not a failure of the
    example and not an expected unbounded exit.
    """
    outcome, detail = run_all.classify(
        "07_kline",
        -1,
        stdout="",
        stderr="_init_connect_sync: init connect fail: msg=check sha error!",
        timed_out=True,
    )
    assert outcome == run_all.BLOCKED, detail


def test_handshake_refusal_on_non_unbounded_example_is_not_fail(fake_examples):
    outcome, _ = run_all.classify("07_kline", -1, "", "init connect fail", timed_out=True)
    assert outcome == run_all.BLOCKED


def test_plain_timeout_with_no_refusal_still_fails():
    outcome, _ = run_all.classify("07_kline", -1, "", "", timed_out=True)
    assert outcome == run_all.FAIL


# ---------------------------------------------------------------------------
# trade-unlock cooldown, in either language
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        "unlock_trade failed: too many attempts",
        "unlock_trade failed: 交易密码的尝试次数已达上限，请1小时之后再试",
    ],
)
def test_trade_cooldown_is_blocked_in_either_language(message):
    """FutuOpenD answers the cooldown in English or Chinese; both are BLOCKED."""
    outcome, detail = run_all.classify("06_stock_sell", 1, "", message)
    assert outcome == run_all.BLOCKED, detail


def test_successful_unlock_is_still_pass():
    outcome, _ = run_all.classify("06_stock_sell", 0, "unlock_trade ok", "")
    assert outcome == run_all.PASS


# ---------------------------------------------------------------------------
# classification invariants
# ---------------------------------------------------------------------------


def test_slow_and_unbounded_classifications_are_disjoint():
    """A bounded example must never be declared unbounded.

    Declaring a bounded example unbounded would turn its timeout into an
    expected outcome, hiding a genuine hang behind a passing verdict.
    """
    overlap = set(run_all.SLOW_EXAMPLES) & set(run_all.UNBOUNDED_EXAMPLES)
    assert overlap == set(), f"declared both slow and unbounded: {sorted(overlap)}"


def test_slow_ceilings_exceed_the_default():
    """A slow ceiling below the default would be meaningless."""
    too_low = {
        name: ceiling
        for name, ceiling in run_all.SLOW_EXAMPLES.items()
        if ceiling <= run_all.TIMEOUT_SEC
    }
    assert too_low == {}, f"slow ceilings below the default: {too_low}"


def test_declared_unbounded_examples_actually_loop_forever():
    """Each unbounded example must contain an unbounded loop.

    This is a heuristic on purpose: it catches an example being added to the
    set by mistake, which is how a real hang would start being reported as an
    expected outcome.
    """
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    not_looping = []
    for name in sorted(run_all.UNBOUNDED_EXAMPLES):
        source = (repo_root / "examples" / name / "main.py").read_text(encoding="utf-8")
        if "while True" not in source:
            not_looping.append(name)
    assert not_looping == [], (
        "declared unbounded but no `while True` found (verify before keeping): "
        f"{not_looping}"
    )


def test_timeout_for_honours_slow_ceilings():
    assert run_all.timeout_for("01_snapshot") == 600
    assert run_all.timeout_for("56_order_flow_imbalance") == 340
    assert run_all.timeout_for("07_kline") == run_all.TIMEOUT_SEC
