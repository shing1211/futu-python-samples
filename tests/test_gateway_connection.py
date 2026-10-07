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

"""Tests for OpenD connection configuration.

These pin the behaviour of the defects that made a live run report every
example as blocked: a wrong RSA key path surfacing as an indefinite SDK retry
instead of an error, and the single-host configuration defaulting to a
different RSA assumption than the host-list configuration.
"""

from __future__ import annotations

import importlib
import os
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "examples"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))


@pytest.fixture()
def connect(monkeypatch):
    """Import examples/connect.py with a controlled environment."""
    monkeypatch.setenv("FUTU_RSA_KEY", "/nonexistent/private_key.pem")
    monkeypatch.delitem(sys.modules, "connect", raising=False)
    return importlib.import_module("connect")


def _reload_connect(monkeypatch, **env):
    for key in ("FUTU_ADDR", "FUTU_OPEND_HOSTS", "FUTU_RSA_KEY"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delitem(sys.modules, "connect", raising=False)
    return importlib.import_module("connect")


# ---------------------------------------------------------------------------
# 8.1 the RSA key is validated before a handshake is attempted
# ---------------------------------------------------------------------------


def test_missing_key_raises(connect):
    with pytest.raises(connect.RsaKeyConfigurationError):
        connect._validate_rsa_key("/nonexistent/private_key.pem")


def test_error_names_the_path_and_the_variables(connect):
    with pytest.raises(connect.RsaKeyConfigurationError) as exc:
        connect._validate_rsa_key("/nonexistent/private_key.pem")
    message = str(exc.value)
    assert "/nonexistent/private_key.pem" in message
    assert "FUTU_RSA_KEY" in message
    assert "FUTU_OPEND_HOSTS" in message


def test_directory_path_raises(tmp_path, monkeypatch):
    module = _reload_connect(monkeypatch, FUTU_RSA_KEY=str(tmp_path))
    with pytest.raises(module.RsaKeyConfigurationError) as exc:
        module._validate_rsa_key(str(tmp_path))
    assert "directory" in str(exc.value)


def test_readable_key_is_accepted(tmp_path, monkeypatch):
    key = tmp_path / "key.pem"
    key.write_text("-- not a real key, only needs to be readable\n", encoding="utf-8")
    module = _reload_connect(monkeypatch, FUTU_RSA_KEY=str(key))
    module._validate_rsa_key(str(key))  # must not raise


def test_configure_rsa_validates_before_enabling(connect, monkeypatch):
    """Validation must happen before the SDK is told to encrypt."""
    calls = []
    monkeypatch.setattr(
        connect.SysConfig, "enable_proto_encrypt", lambda e: calls.append(("encrypt", e))
    )
    monkeypatch.setattr(
        connect.SysConfig, "set_init_rsa_file", lambda f: calls.append(("key", f))
    )
    with pytest.raises(connect.RsaKeyConfigurationError):
        connect.configure_rsa(True)
    assert calls == [], f"SDK was configured despite an unusable key: {calls}"


def test_configure_rsa_skips_validation_when_disabled(connect, monkeypatch):
    calls = []
    monkeypatch.setattr(
        connect.SysConfig, "enable_proto_encrypt", lambda e: calls.append(("encrypt", e))
    )
    monkeypatch.setattr(
        connect.SysConfig, "set_init_rsa_file", lambda f: calls.append(("key", f))
    )
    connect.configure_rsa(False)
    assert calls == [("encrypt", False)], calls


def test_no_context_is_constructed_when_the_key_is_bad(connect, monkeypatch):
    """A bad key must not reach OpenQuoteContext, which would never return."""
    constructed = []
    monkeypatch.setattr(
        connect,
        "OpenQuoteContext",
        lambda **kw: constructed.append(kw),
    )
    with pytest.raises(connect.RsaKeyConfigurationError):
        connect.create_quote_context()
    assert constructed == [], "OpenQuoteContext was constructed despite a bad key"


def test_error_is_a_runtime_error(connect):
    """Callers catching RuntimeError keep working."""
    assert issubclass(connect.RsaKeyConfigurationError, RuntimeError)


# ---------------------------------------------------------------------------
# 8.2 single-host and host-list configuration agree on RSA
# ---------------------------------------------------------------------------


def test_single_host_defaults_to_rsa(monkeypatch):
    module = _reload_connect(monkeypatch, FUTU_ADDR="127.0.0.1:11111")
    hosts = module._parse_hosts()
    assert hosts == [("127.0.0.1", 11111, True)]


def test_same_host_agrees_across_both_variables(monkeypatch):
    """The bug: one host, two variables, two different RSA answers."""
    via_addr = _reload_connect(monkeypatch, FUTU_ADDR="127.0.0.1:11111")._parse_hosts()
    via_list = _reload_connect(
        monkeypatch, FUTU_OPEND_HOSTS="127.0.0.1:11111"
    )._parse_hosts()
    assert via_addr == via_list, f"{via_addr} != {via_list}"


def test_explicit_false_overrides_the_default(monkeypatch):
    module = _reload_connect(
        monkeypatch, FUTU_OPEND_HOSTS="127.0.0.1:11111:False"
    )._parse_hosts()
    assert module[0][2] is False


def test_explicit_true_is_preserved(monkeypatch):
    module = _reload_connect(
        monkeypatch, FUTU_OPEND_HOSTS="127.0.0.1:11111:True"
    )._parse_hosts()
    assert module[0][2] is True


def test_host_without_port_defaults_to_11111(monkeypatch):
    module = _reload_connect(monkeypatch, FUTU_OPEND_HOSTS="127.0.0.1")._parse_hosts()
    assert module[0][1] == 11111


def test_ha_list_is_parsed_per_host(monkeypatch):
    module = _reload_connect(
        monkeypatch,
        FUTU_OPEND_HOSTS="10.0.0.1:11111:True,10.0.0.2:22222:False",
    )._parse_hosts()
    assert module == [("10.0.0.1", 11111, True), ("10.0.0.2", 22222, False)]


# ---------------------------------------------------------------------------
# 8.3 handshake-refusal patterns are scoped to the timeout path
# ---------------------------------------------------------------------------


def test_nonzero_exit_with_check_sha_is_fail():
    import run_all

    outcome, _ = run_all.classify("07_kline", 1, "", "check sha error")
    assert outcome == run_all.FAIL


def test_timeout_with_check_sha_is_blocked():
    import run_all

    outcome, _ = run_all.classify("07_kline", -1, "", "check sha error", timed_out=True)
    assert outcome == run_all.BLOCKED


def test_nonzero_exit_with_init_connect_fail_is_fail():
    import run_all

    outcome, _ = run_all.classify("07_kline", 1, "", "init connect fail")
    assert outcome == run_all.FAIL


def test_unambiguous_refusals_apply_on_both_paths():
    import run_all

    for text in (
        "No reachable OpenD gateways",
        "Failed to connect to any host",
        "connection refused",
        "unlock_trade failed: too many attempts",
        "No event contract quote permission",
        "quote login failed",
    ):
        assert run_all.classify("x", 1, "", text)[0] == run_all.BLOCKED, text
        assert (
            run_all.classify("x", -1, "", text, timed_out=True)[0] == run_all.BLOCKED
        ), text


def test_timeout_patterns_are_not_applied_on_clean_exit():
    import run_all

    assert run_all.classify("x", 0, "", "check sha error")[0] == run_all.PASS


# ---------------------------------------------------------------------------
# 8.4 .env.example states the local-gateway RSA requirement
# ---------------------------------------------------------------------------


def test_env_example_states_local_rsa_requirement():
    text = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "localhost" in lowered
    assert "rsa" in lowered
    # It must no longer imply localhost needs no RSA.
    assert "is_rsa=False for localhost" not in text


def test_env_example_has_no_private_range_hosts():
    text = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "172.18." not in text
    assert "172.20." not in text


def test_env_example_documents_the_false_escape_hatch():
    text = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "is_rsa=False" in text


def test_env_example_names_the_futu_xml_key_location():
    text = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "rsa_private_key" in text


def test_connect_ha_example_does_not_default_to_no_rsa():
    """The teaching example must not demonstrate the superseded default."""
    source = (REPO_ROOT / "examples" / "00_connect_ha" / "main.py").read_text("utf-8")
    assert "return [(host, int(port_str), True)]" in source
    assert "return [(host, int(port_str), False)]" not in source


def test_connect_ha_example_validates_its_key():
    source = (REPO_ROOT / "examples" / "00_connect_ha" / "main.py").read_text("utf-8")
    assert "does not exist" in source