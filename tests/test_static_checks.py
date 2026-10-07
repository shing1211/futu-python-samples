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

"""Tests for the static verification tier.

Every check is exercised against a fixture tree it controls, and separately
against the real repository where the task list asserts a known count. The
fixture cases matter most: they pin each check's real behavior rather than
accepting whatever it happens to report today.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import static_checks
from static_checks.core import (
    SEVERITY_FAIL,
    SEVERITY_REPORT,
    RepoContext,
    blocking,
    discover_example_dirs,
    names,
    run_checks,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

HEADER = '"""\nLicensed under the Apache License\n"""'


def make_repo(tmp_path: pathlib.Path, files: dict[str, str]) -> RepoContext:
    """Build a minimal repository tree and return a context over it.

    ``examples/connect.py`` is always present unless the caller supplies one, so
    that skeleton checks see the directory they are meant to reach.
    """
    for rel, body in files.items():
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    (tmp_path / "examples").mkdir(exist_ok=True)
    if not (tmp_path / "examples" / "connect.py").exists():
        (tmp_path / "examples" / "connect.py").write_text("x = 1\n", encoding="utf-8")
    return static_checks.context_for(tmp_path)


def run_one(ctx: RepoContext, name: str):
    static_checks.load_all()
    return static_checks.get(name).run(ctx)


def messages(findings) -> str:
    return "\n".join(f.message for f in findings)


# ---------------------------------------------------------------------------
# 2.1 byte-compilation
# ---------------------------------------------------------------------------


def test_byte_compilation_reports_unparseable_file(tmp_path):
    ctx = make_repo(
        tmp_path,
        {
            "examples/00_good/main.py": "x = 1\n",
            "examples/01_broken/main.py": "def (:\n",
        },
    )
    findings = run_one(ctx, "byte-compilation")
    assert len(findings) == 1
    assert findings[0].path.endswith("01_broken/main.py")
    assert findings[0].severity == SEVERITY_FAIL


def test_byte_compilation_clean_tree_is_silent(tmp_path):
    ctx = make_repo(tmp_path, {"examples/00_ok/main.py": "x = 1\n"})
    assert run_one(ctx, "byte-compilation") == []


def test_byte_compilation_repository_is_clean():
    ctx = static_checks.context_for(REPO_ROOT)
    assert run_one(ctx, "byte-compilation") == []


# ---------------------------------------------------------------------------
# 2.2 license header (report-only)
# ---------------------------------------------------------------------------


def test_license_header_reports_missing_header(tmp_path):
    ctx = make_repo(
        tmp_path,
        {
            "examples/00_ok/main.py": HEADER + "\n",
            "examples/01_bare/main.py": "x = 1\n",
        },
    )
    findings = run_one(ctx, "license-header")
    missing = [f for f in findings if f.severity == SEVERITY_REPORT]
    assert len(missing) == 1
    assert "01_bare" in missing[0].path


def test_license_header_is_report_only_so_never_blocks(tmp_path):
    ctx = make_repo(tmp_path, {"examples/01_bare/main.py": "x = 1\n"})
    assert blocking(run_one(ctx, "license-header")) == []


def test_license_header_surfaces_the_sixteen_known_files():
    """The 16 headerless files are reported, and fixing them is out of scope."""
    ctx = static_checks.context_for(REPO_ROOT)
    findings = [
        f for f in run_one(ctx, "license-header") if f.severity == SEVERITY_REPORT
    ]
    assert len(findings) == 16, messages(findings)
    paths = {f.path for f in findings}
    assert "examples/99_financial_statements/main.py" in paths
    assert "examples/114_valuation_heatmap/main.py" in paths
    assert not any(p.startswith("examples/0") for p in paths)


# ---------------------------------------------------------------------------
# 2.3 example skeleton
# ---------------------------------------------------------------------------


def test_skeleton_reports_missing_main_guard(tmp_path):
    body = "import sys\nprint(sys.path)\n"
    ctx = make_repo(tmp_path, {"examples/00_unguarded/main.py": body})
    findings = run_one(ctx, "example-skeleton")
    assert any("__main__" in f.message for f in findings)


def test_skeleton_reports_inverted_import_order(tmp_path):
    body = (
        "import sys\n"
        "from pathlib import Path\n"
        "import futu as ft\n"
        "sys.path.insert(0, str(Path(__file__).parent.parent))\n"
        "from connect import create_quote_context\n"
        'if __name__ == "__main__":\n'
        "    pass\n"
    )
    ctx = make_repo(tmp_path, {"examples/00_inverted/main.py": body})
    findings = run_one(ctx, "example-skeleton")
    assert any("import futu` precedes" in f.message for f in findings)
    assert not any("connect" in f.message for f in findings)


def test_skeleton_accepts_correct_order(tmp_path):
    body = (
        "import sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).parent.parent))\n"
        "import futu as ft\n"
        "from connect import create_quote_context\n"
        'if __name__ == "__main__":\n'
        "    ctx = create_quote_context()\n"
        "    ctx.close()\n"
    )
    ctx = make_repo(tmp_path, {"examples/00_ok/main.py": body})
    assert run_one(ctx, "example-skeleton") == []


def test_skeleton_reports_unclosed_context(tmp_path):
    body = (
        "import sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).parent.parent))\n"
        "from connect import create_quote_context\n"
        'if __name__ == "__main__":\n'
        "    ctx = create_quote_context()\n"
        "    print(ctx)\n"
    )
    ctx = make_repo(tmp_path, {"examples/00_leak/main.py": body})
    findings = run_one(ctx, "example-skeleton")
    assert any("never calls .close()" in f.message for f in findings)


def test_skeleton_repository_has_no_violations():
    """The two unguarded examples and three inverted imports were fixed in 4.2."""
    ctx = static_checks.context_for(REPO_ROOT)
    failures = [
        f for f in run_one(ctx, "example-skeleton") if f.severity == SEVERITY_FAIL
    ]
    assert failures == [], messages(failures)


# ---------------------------------------------------------------------------
# 2.4 error suppression
# ---------------------------------------------------------------------------


def test_suppression_detects_pass_only_handler(tmp_path):
    body = "try:\n    risky()\nexcept Exception:\n    pass\n"
    ctx = make_repo(tmp_path, {"examples/00_x/main.py": body})
    findings = run_one(ctx, "error-suppression")
    assert len(findings) == 1
    assert findings[0].line == 3


def test_suppression_detects_continue_only_handler(tmp_path):
    body = "for _ in x:\n    try:\n        f()\n    except Exception:\n        continue\n"
    ctx = make_repo(tmp_path, {"examples/00_x/main.py": body})
    assert len(run_one(ctx, "error-suppression")) == 1


def test_suppression_allows_log_and_reraise(tmp_path):
    body = (
        "try:\n"
        "    risky()\n"
        "except Exception as exc:\n"
        "    logger.error('failed: %s', exc)\n"
        "    raise\n"
    )
    ctx = make_repo(tmp_path, {"examples/00_x/main.py": body})
    assert run_one(ctx, "error-suppression") == []


def test_suppression_repository_has_no_unreviewed_sites():
    """Every suppression site is either fixed or carries a recorded justification.

    examples/67_health_monitor previously had five unreviewed handlers that made
    the monitor report healthy when nothing worked; task 4.1 recorded the probe
    failures instead. The remaining sites are reviewed narrow cases carrying an
    inline allow-suppress marker.
    """
    ctx = static_checks.context_for(REPO_ROOT)
    findings = run_one(ctx, "error-suppression")
    assert findings == [], messages(findings)


def test_suppression_marker_suppresses_the_finding(tmp_path):
    body = (
        "try:\n"
        "    listen()\n"
        "except KeyboardInterrupt:\n"
        "    pass  # static-checks: allow-suppress -- Ctrl-C ends the loop\n"
    )
    ctx = make_repo(tmp_path, {"examples/00_x/main.py": body})
    assert run_one(ctx, "error-suppression") == []


def test_suppression_without_marker_is_still_reported(tmp_path):
    """A marker on one site must not excuse an unreviewed sibling."""
    body = (
        "try:\n"
        "    a()\n"
        "except KeyboardInterrupt:\n"
        "    pass  # static-checks: allow-suppress -- reviewed\n"
        "try:\n"
        "    b()\n"
        "except Exception:\n"
        "    pass\n"
    )
    ctx = make_repo(tmp_path, {"examples/00_x/main.py": body})
    findings = run_one(ctx, "error-suppression")
    assert len(findings) == 1
    assert findings[0].line == 7


def test_suppression_allows_log_then_continue(tmp_path):
    """Logging the failure keeps it observable, so this is not suppression."""
    body = (
        "for code in codes:\n"
        "    try:\n"
        "        analyze(code)\n"
        "    except Exception as exc:\n"
        "        logger.warning('failed: %s', exc)\n"
        "        continue\n"
    )
    ctx = make_repo(tmp_path, {"examples/00_x/main.py": body})
    assert run_one(ctx, "error-suppression") == []


def test_suppression_is_report_only(tmp_path):
    body = "try:\n    risky()\nexcept Exception:\n    pass\n"
    ctx = make_repo(tmp_path, {"examples/00_x/main.py": body})
    assert blocking(run_one(ctx, "error-suppression")) == []


# ---------------------------------------------------------------------------
# 2.5 dead constant
# ---------------------------------------------------------------------------


def test_dead_constant_flags_unread_constant(tmp_path):
    body = "UNUSED = {1, 2}\nOTHER = 3\nprint(OTHER)\n"
    ctx = make_repo(tmp_path, {"scripts/tool.py": body})
    findings = run_one(ctx, "dead-constant")
    assert len(findings) == 1
    assert "UNUSED" in findings[0].message


def test_dead_constant_allows_constant_read_by_another_module(tmp_path):
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "scripts/lib.py").write_text("EXPORTED = 1\n", encoding="utf-8")
    (tmp_path / "scripts/main.py").write_text(
        "from lib import EXPORTED\nprint(EXPORTED)\n", encoding="utf-8"
    )
    ctx = make_repo(tmp_path, {})
    assert run_one(ctx, "dead-constant") == []


def test_dead_constant_allows_dunder_all_entry(tmp_path):
    body = "EXPORTED = 1\n__all__ = ['EXPORTED']\n"
    ctx = make_repo(tmp_path, {"scripts/lib.py": body})
    assert run_one(ctx, "dead-constant") == []


def test_dead_constant_trade_examples_was_the_known_defect():
    """The defect this check was written for: TRADE_EXAMPLES in run_all.py.

    It was assigned at task 2.5 and removed at task 3.5, so the check now
    reports nothing for that file. This test pins that the fix stayed applied.
    """
    source = (REPO_ROOT / "scripts" / "run_all.py").read_text(encoding="utf-8")
    assert "TRADE_EXAMPLES" not in source, (
        "TRADE_EXAMPLES was removed in task 3.5; reintroducing it would "
        "reintroduce a classification that is never consulted"
    )


def test_dead_constant_repository_is_clean_after_rework():
    """Once group 3 lands, run_all.py must have no unread constants."""
    ctx = static_checks.context_for(REPO_ROOT)
    findings = [f for f in run_one(ctx, "dead-constant") if "run_all.py" in f.path]
    assert findings == [], messages(findings)


# ---------------------------------------------------------------------------
# 2.6 index coverage
# ---------------------------------------------------------------------------


INDEX = (
    "| # | Name |\n|---|------|\n"
    "| [00](./00_a/) | A |\n"
    "| [01](./01_b/) | B |\n"
)


def test_index_coverage_reports_unindexed_directory(tmp_path):
    ctx = make_repo(
        tmp_path,
        {
            "examples/00_a/main.py": "",
            "examples/01_b/main.py": "",
            "examples/02_c/main.py": "",
            "examples/README.md": INDEX,
        },
    )
    findings = run_one(ctx, "index-coverage")
    unindexed = [f for f in findings if "not listed" in f.message]
    assert len(unindexed) == 1
    assert "02_c" in unindexed[0].path


def test_index_coverage_reports_multi_section_example(tmp_path):
    doubled = INDEX + "\n| [00](./00_a/) | A again |\n"
    ctx = make_repo(
        tmp_path,
        {
            "examples/00_a/main.py": "",
            "examples/01_b/main.py": "",
            "examples/README.md": doubled,
        },
    )
    findings = [f for f in run_one(ctx, "index-coverage") if "sections" in f.message]
    assert len(findings) == 1
    assert "00_a is indexed in 2 sections" in findings[0].message


def test_index_coverage_reports_phantom_index_entry(tmp_path):
    phantom = INDEX + "| [09](./09_ghost/) | Ghost |\n"
    ctx = make_repo(
        tmp_path,
        {
            "examples/00_a/main.py": "",
            "examples/01_b/main.py": "",
            "examples/README.md": phantom,
        },
    )
    findings = run_one(ctx, "index-coverage")
    phantom_findings = [f for f in findings if "not an example directory" in f.message]
    assert len(phantom_findings) == 1
    assert phantom_findings[0].severity == SEVERITY_FAIL


def test_index_coverage_repository_counts():
    ctx = static_checks.context_for(REPO_ROOT)
    findings = run_one(ctx, "index-coverage")
    unindexed = [f for f in findings if "not listed" in f.message]
    multi = [f for f in findings if "sections" in f.message]
    phantom = [f for f in findings if "not an example directory" in f.message]
    assert len(unindexed) == 26, messages(unindexed)
    assert len(multi) == 8, messages(multi)
    assert phantom == [], messages(phantom)


# ---------------------------------------------------------------------------
# 2.7 contract table duplication
# ---------------------------------------------------------------------------


def test_contract_duplication_flags_shared_table(tmp_path):
    body = "### Return Type Reference\n\n| API | shape |\n"
    ctx = make_repo(tmp_path, {"AGENTS.md": body, "CONTRIBUTING.md": body})
    findings = run_one(ctx, "contract-table-duplication")
    assert findings
    assert "appears in 2 documents" in findings[0].message


def test_contract_duplication_silent_for_single_document(tmp_path):
    body = "### Return Type Reference\n"
    ctx = make_repo(tmp_path, {"AGENTS.md": body, "CONTRIBUTING.md": "nothing here"})
    assert run_one(ctx, "contract-table-duplication") == []


def test_contract_duplication_repository_flags_agents_and_contributing():
    ctx = static_checks.context_for(REPO_ROOT)
    findings = run_one(ctx, "contract-table-duplication")
    assert findings, "AGENTS.md and CONTRIBUTING.md share contract tables"
    assert all("AGENTS.md" in f.path and "CONTRIBUTING.md" in f.path for f in findings)


# ---------------------------------------------------------------------------
# 2.8 registry and runner
# ---------------------------------------------------------------------------


def test_registry_exposes_the_seven_checks():
    assert set(names()) == {
        "byte-compilation",
        "contract-table-duplication",
        "dead-constant",
        "error-suppression",
        "example-skeleton",
        "index-coverage",
        "license-header",
    }


def test_registry_instances_are_independent():
    static_checks.load_all()
    first, second = static_checks.get("index-coverage"), static_checks.get("index-coverage")
    assert first is not second


def test_run_checks_can_select_a_subset(tmp_path):
    ctx = make_repo(tmp_path, {"examples/00_x/main.py": "x = 1\n"})
    findings = run_checks(ctx, ["byte-compilation"])
    assert findings == []


GOOD_MAIN = (
    HEADER
    + "\nimport sys\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, str(Path(__file__).parent.parent))\n"
    "import futu as ft\n"
    "from connect import create_quote_context\n"
    'if __name__ == "__main__":\n'
    "    ctx = create_quote_context()\n"
    "    ctx.close()\n"
)

CLEAN_INDEX = "| # | Name |\n|---|------|\n| [00](./00_ok/) | Ok |\n"


def write_clean_tree(tmp_path: pathlib.Path) -> pathlib.Path:
    """A tree that satisfies every check, for runner exit-status tests."""
    example = tmp_path / "examples" / "00_ok"
    example.mkdir(parents=True)
    (example / "main.py").write_text(GOOD_MAIN, encoding="utf-8")
    (tmp_path / "examples" / "connect.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "examples" / "README.md").write_text(CLEAN_INDEX, encoding="utf-8")
    return tmp_path


def test_runner_exits_zero_on_clean_tree(tmp_path):
    write_clean_tree(tmp_path)
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_static.py"), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "STATIC" in proc.stdout


def test_runner_exits_one_when_blocking_finding_present(tmp_path):
    write_clean_tree(tmp_path)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "m.py").write_text("NEVER_READ = 1\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_static.py"), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "NEVER_READ" in proc.stdout


def test_runner_rejects_unknown_check_name(tmp_path):
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "run_static.py"),
            "--root",
            str(tmp_path),
            "--checks",
            "no-such-check",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "unknown check" in proc.stderr


def test_runner_output_cannot_be_read_as_a_live_result():
    """The banner must state the tier boundary in the output itself."""
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_static.py"), "--list"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    full = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_static.py"), "--root", "/nonexistent"],
        capture_output=True,
        text=True,
    )
    text = full.stdout + full.stderr
    assert "does NOT" in text
    assert "run_all.py" in text


def test_discovery_orders_numerically_not_lexicographically(tmp_path):
    for name in ("00_a", "9_b", "100_c", "127_d", "45b_e"):
        (tmp_path / "examples" / name).mkdir(parents=True)
    found = discover_example_dirs(tmp_path)
    assert list(found) == ["00_a", "9_b", "45b_e", "100_c", "127_d"]

# ---------------------------------------------------------------------------
# example-skeleton: the inserted path must actually reach connect.py
# ---------------------------------------------------------------------------


def test_skeleton_reports_path_without_connect_module(tmp_path):
    """Ordering is not enough: the right directory must be on the path.

    This is the defect in examples/57_vwap_benchmark, which inserted the
    repository root while connect.py lives in examples/.
    """
    body = (
        "import sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).parent.parent))\n"
        "import futu as ft\n"
        "from connect import create_quote_context\n"
        'if __name__ == "__main__":\n'
        "    create_quote_context().close()\n"
    )
    ctx = make_repo(tmp_path, {"examples/00_x/main.py": body})
    # This case is specifically about a tree where connect.py is absent.
    (tmp_path / "examples" / "connect.py").unlink()
    findings = [f for f in run_one(ctx, "example-skeleton") if "connect.py" in f.message]
    assert len(findings) == 1, messages(findings)


def test_skeleton_accepts_extra_insert_for_sibling_helpers(tmp_path):
    """Inserting its own directory for sibling helpers is legitimate."""
    (tmp_path / "examples" / "00_x").mkdir(parents=True)
    (tmp_path / "examples" / "connect.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "examples" / "00_x" / "helper.py").write_text("y = 2\n", encoding="utf-8")
    body = (
        "import sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).parent.parent))\n"
        "sys.path.insert(0, str(Path(__file__).parent))\n"
        "import futu as ft\n"
        "from connect import create_quote_context\n"
        'if __name__ == "__main__":\n'
        "    create_quote_context().close()\n"
    )
    ctx = make_repo(tmp_path, {"examples/00_x/main.py": body})
    assert run_one(ctx, "example-skeleton") == []


def test_skeleton_resolves_module_level_alias(tmp_path):
    """An alias built from __file__ must resolve the way it will at runtime."""
    (tmp_path / "examples" / "00_x").mkdir(parents=True)
    (tmp_path / "examples" / "connect.py").write_text("x = 1\n", encoding="utf-8")
    body = (
        "import sys\n"
        "from pathlib import Path\n"
        "_EX = str(Path(__file__).resolve().parent.parent)\n"
        "if _EX not in sys.path:\n"
        "    sys.path.insert(0, _EX)\n"
        "import futu as ft\n"
        "from connect import create_quote_context\n"
        'if __name__ == "__main__":\n'
        "    create_quote_context().close()\n"
    )
    ctx = make_repo(tmp_path, {"examples/00_x/main.py": body})
    assert run_one(ctx, "example-skeleton") == []


def test_skeleton_repository_has_no_path_defects():
    ctx = static_checks.context_for(REPO_ROOT)
    failures = [
        f for f in run_one(ctx, "example-skeleton") if f.severity == SEVERITY_FAIL
    ]
    assert failures == [], messages(failures)
