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

"""The static verification tier's check set.

This is the closed set from design.md Decision 5. Each check decides one
property from source alone and reports findings; none of them asserts anything
about runtime behavior, and none may be widened to do so.

Adding a property here is a deliberate act. A check that cannot be decided
without executing an example belongs to the live tier, not this one.
"""

from __future__ import annotations

import ast
import os as _os
import pathlib
import py_compile
import re

from .core import (
    SEVERITY_FAIL,
    SEVERITY_INFO,
    SEVERITY_REPORT,
    Finding,
    RepoContext,
    register,
)

LICENSE_MARKER = "Licensed under the Apache License"

#: Contract tables that are currently duplicated across prose documents.
CONTRACT_TABLE_HEADINGS = (
    "Return types that differ from the docs",
    "Enum names that don't exist",
    "pandas traps",
    "Return Type Reference",
    "Code Conventions",
)

CONTRACT_DOCUMENTS = ("AGENTS.md", "CONTRIBUTING.md")


# ---------------------------------------------------------------------------
# 2.1 byte-compilation
# ---------------------------------------------------------------------------


class ByteCompilationCheck:
    name = "byte-compilation"
    description = "Every example file compiles."

    def run(self, ctx: RepoContext) -> list[Finding]:
        findings: list[Finding] = []
        for path in ctx.python_files():
            try:
                py_compile.compile(
                    str(path), cfile=str(path) + ".staticcheck.pyc", doraise=True
                )
            except py_compile.PyCompileError as exc:
                findings.append(
                    Finding(
                        check=self.name,
                        path=ctx.rel(path),
                        message=f"does not compile: {exc.msg.strip()}",
                        severity=SEVERITY_FAIL,
                    )
                )
            finally:
                _unlink(path.with_suffix(path.suffix + ".staticcheck.pyc"))
        return findings


def _unlink(path: pathlib.Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass


# ---------------------------------------------------------------------------
# 2.2 license header (report-only)
# ---------------------------------------------------------------------------


class LicenseHeaderCheck:
    """Measures header coverage.

    Report-only by design: 16 example files are missing the header, and fixing
    them is outside this change's scope. See tasks.md 2.2 -- promoting this to a
    failing gate is blocked until those files are fixed.
    """

    name = "license-header"
    description = "Every example file carries the Apache license header (report-only)."

    def run(self, ctx: RepoContext) -> list[Finding]:
        findings: list[Finding] = []
        files = ctx.python_files()
        for path in files:
            try:
                head = path.read_text(encoding="utf-8", errors="replace")[:2048]
            except OSError:
                continue
            if LICENSE_MARKER not in head:
                findings.append(
                    Finding(
                        check=self.name,
                        path=ctx.rel(path),
                        message=f"missing Apache license header ({LICENSE_MARKER!r})",
                        severity=SEVERITY_REPORT,
                    )
                )
        if files and not findings:
            findings.append(
                Finding(
                    check=self.name,
                    path=ctx.rel(ctx.examples_dir),
                    message=f"header present on all {len(files)} example files",
                    severity=SEVERITY_INFO,
                )
            )
        return findings


# ---------------------------------------------------------------------------
# 2.3 example skeleton
# ---------------------------------------------------------------------------


class ExampleSkeletonCheck:
    """The documented example skeleton from CONTRIBUTING.md.

    Three properties: a ``__main__`` guard, ``sys.path`` insertion ordered
    before the ``futu``/``connect`` imports, and context cleanup on every
    context-creating path.
    """

    name = "example-skeleton"
    description = "Examples follow the documented skeleton."

    def run(self, ctx: RepoContext) -> list[Finding]:
        findings: list[Finding] = []
        for path in ctx.python_files():
            rel = ctx.rel(path)
            if path.name != "main.py":
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError as exc:
                findings.append(
                    Finding(
                        check=self.name,
                        path=rel,
                        message=f"cannot parse for skeleton check: {exc.msg}",
                        line=exc.lineno,
                        severity=SEVERITY_REPORT,
                    )
                )
                continue
            findings.extend(self._main_guard(tree, rel))
            findings.extend(self._import_order(tree, rel))
            findings.extend(self._context_cleanup(tree, rel))
            findings.extend(self._path_resolves_to_connect(tree, rel, path))
        return findings

    def _main_guard(self, tree: ast.Module, rel: str) -> list[Finding]:
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                test = node.test
                if (
                    isinstance(test, ast.Compare)
                    and isinstance(test.left, ast.Name)
                    and test.left.id == "__name__"
                ):
                    return []
        return [
            Finding(
                check=self.name,
                path=rel,
                message="no `if __name__ == \"__main__\":` guard at module level",
                severity=SEVERITY_FAIL,
            )
        ]

    def _path_resolves_to_connect(
        self, tree: ast.Module, rel: str, path: pathlib.Path
    ) -> list[Finding]:
        """At least one inserted directory must actually contain ``connect.py``.

        Ordering alone is not enough. An example can insert its path before its
        imports perfectly and still be unable to import anything, because it put
        the wrong directory on the path -- the repository root instead of
        ``examples/``. That failure only appears at runtime as
        ``ModuleNotFoundError: No module named 'connect'``.

        An example may legitimately insert several directories: its own, to
        reach sibling helper modules, plus ``examples/`` to reach ``connect``.
        So the property is that at least one insert makes ``connect`` importable,
        not that every insert does.

        The inserted expression is evaluated in a restricted namespace seeded
        with this file's own location, so ``Path(__file__).parent.parent`` and
        any module-level alias built from it resolve the way they will at runtime.
        """
        namespace = self._namespace(tree, path)
        inserts: list[tuple[int, str, pathlib.Path]] = []
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "insert"
                and len(node.args) >= 2
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == 0
            ):
                continue
            try:
                expr = ast.unparse(node.args[1])
            except Exception:  # unparse can fail on exotic nodes
                continue
            resolved = self._resolve_path(expr, namespace)
            if resolved is not None:
                inserts.append((node.lineno, expr, resolved))

        if not inserts:
            return []
        if any((resolved / "connect.py").is_file() for _, _, resolved in inserts):
            return []

        tried = "; ".join(f"{expr} -> {resolved}" for _, expr, resolved in inserts)
        return [
            Finding(
                check=self.name,
                path=rel,
                message=(
                    f"no sys.path.insert resolves to a directory containing "
                    f"connect.py, so `from connect import ...` will raise "
                    f"ModuleNotFoundError. Inserts: {tried}"
                ),
                line=inserts[0][0],
                severity=SEVERITY_FAIL,
            )
        ]

    @staticmethod
    def _namespace(tree: ast.Module, path: pathlib.Path) -> dict:
        """A restricted namespace for evaluating path expressions.

        Seeded with this example's location plus any module-level string alias
        built from it, so an indirection like ``_REPO_ROOT`` resolves too.
        """
        namespace: dict = {
            "__file__": str(path),
            "Path": pathlib.Path,
            "str": str,
            "os": _os,
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and target.id.isidentifier():
                    try:
                        namespace[target.id] = eval(
                            compile(ast.Expression(node.value), "<expr>", "eval"),
                            {"__builtins__": {}},
                            namespace,
                        )
                    except Exception:
                        continue
        return namespace

    @staticmethod
    def _resolve_path(expr: str, namespace: dict) -> pathlib.Path | None:
        try:
            value = eval(
                compile(expr, "<expr>", "eval"), {"__builtins__": {}}, namespace
            )
        except Exception:
            return None
        if not isinstance(value, (str, pathlib.Path)):
            return None
        try:
            return pathlib.Path(value)
        except (TypeError, ValueError):
            return None

    def _import_order(self, tree: ast.Module, rel: str) -> list[Finding]:
        """A ``futu``/``connect`` import must follow ``sys.path.insert(0, ...)``.

        Ordering is decided by source position, so the relevant nodes are
        collected and then sorted by line. Walking the tree directly would
        visit them in breadth-first order and compare the wrong lines.
        """
        events: list[tuple[int, int, str, str]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr == "insert"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and node.args[0].value == 0
                ):
                    events.append((node.lineno, 0, "", ""))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in {"futu", "connect"}:
                        events.append((node.lineno, 1, alias.name, "import"))
            elif isinstance(node, ast.ImportFrom) and node.module in {"futu", "connect"}:
                events.append((node.lineno, 1, node.module, "from"))

        events.sort()
        seen_insert = False
        bad: list[Finding] = []
        for lineno, kind, module, form in events:
            if kind == 0:
                seen_insert = True
                continue
            if seen_insert:
                continue
            if form == "import":
                message = (
                    f"`import {module}` precedes sys.path.insert(0, ...); may "
                    "resolve a system-wide package"
                )
            else:
                message = f"`from {module} import ...` precedes sys.path.insert(0, ...)"
            bad.append(
                Finding(
                    check=self.name,
                    path=rel,
                    message=message,
                    line=lineno,
                    severity=SEVERITY_FAIL,
                )
            )
        return bad

    def _context_cleanup(self, tree: ast.Module, rel: str) -> list[Finding]:
        creates = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"create_quote_context", "create_trade_context"}
            for node in ast.walk(tree)
        )
        if not creates:
            return []
        closes = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "close"
            for node in ast.walk(tree)
        )
        if closes:
            return []
        return [
            Finding(
                check=self.name,
                path=rel,
                message="creates a context but never calls .close() on it",
                severity=SEVERITY_FAIL,
            )
        ]


# ---------------------------------------------------------------------------
# 2.4 error suppression
# ---------------------------------------------------------------------------


class ErrorSuppressionCheck:
    """Exception handlers whose entire body is ``pass`` or ``continue``.

    Such a handler makes a failure unobservable, which defeats a runner that
    trusts exit status. The check reports sites for human review rather than
    failing outright: suppression is sometimes correct in a monitor loop that
    must survive a transient error, and design.md records that judgement as a
    human one.

    A handler that records the failure -- logs it, counts it, re-raises it --
    is not suppression, because the failure stays observable. Only a handler
    whose entire body is ``pass`` or ``continue`` hides anything, and that is
    what this check reports.

    A reviewed site opts out with an inline marker on the handler, which keeps
    the justification next to the code a reviewer will actually read and lets
    the decision survive line movement::

        except KeyboardInterrupt:
            pass  # static-checks: allow-suppress -- Ctrl-C ends the listen loop

    Any site without the marker is reported, so a newly added suppression
    cannot inherit an earlier review by accident.
    """

    name = "error-suppression"
    description = "Exception handlers that suppress every failure (report-only)."

    MARKER = "allow-suppress"

    def run(self, ctx: RepoContext) -> list[Finding]:
        findings: list[Finding] = []
        for path in ctx.python_files():
            try:
                source = path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source)
            except SyntaxError:
                continue
            lines = source.splitlines()
            for node in ast.walk(tree):
                if not isinstance(node, ast.ExceptHandler):
                    continue
                body = self._significant_body(node)
                if not body or not all(
                    isinstance(s, (ast.Pass, ast.Continue)) for s in body
                ):
                    continue
                if self._reviewed(source, lines, node):
                    continue
                findings.append(
                    Finding(
                        check=self.name,
                        path=ctx.rel(path),
                        message=(
                            "exception handler body is only pass/continue and "
                            f"carries no '{self.MARKER}' justification"
                        ),
                        line=node.lineno,
                        severity=SEVERITY_REPORT,
                    )
                )
        return findings

    @staticmethod
    def _significant_body(node: ast.ExceptHandler) -> list[ast.stmt]:
        """Handler statements that actually do something.

        A docstring or a bare constant expression is not a statement of intent,
        so it is dropped. A call expression is: logging the failure makes it
        observable, which is the whole point of the check.
        """
        body = []
        for stmt in node.body:
            if isinstance(stmt, ast.Expr) and not isinstance(stmt.value, ast.Call):
                continue
            body.append(stmt)
        return body

    @classmethod
    def _reviewed(cls, source: str, lines: list[str], node: ast.ExceptHandler) -> bool:
        """True when the handler carries an allow-suppress marker.

        Accepts a marker on the pass/continue statement or on the handler's own
        line, so either placement works.
        """
        candidates = {node.lineno}
        candidates.update(
            stmt.lineno
            for stmt in node.body
            if isinstance(stmt, (ast.Pass, ast.Continue))
        )
        for stmt in node.body:
            if isinstance(stmt, (ast.Pass, ast.Continue)) and stmt.end_lineno:
                candidates.add(stmt.end_lineno)
        for lineno in candidates:
            if 1 <= lineno <= len(lines) and cls.MARKER in lines[lineno - 1]:
                return True
        return False


# ---------------------------------------------------------------------------
# 2.5 dead module-level constants
# ---------------------------------------------------------------------------


class DeadConstantCheck:
    """Uppercase module-level assignments that are never read.

    A constant that another module imports counts as read. Without that, a
    re-exported constant would be reported as dead by the very module that
    re-exports it.
    """

    name = "dead-constant"
    description = "Uppercase module-level constants that are never read."

    def run(self, ctx: RepoContext) -> list[Finding]:
        candidates = self._candidate_files(ctx)
        trees: dict[pathlib.Path, ast.Module] = {}
        for path in candidates:
            try:
                trees[path] = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
            except (OSError, SyntaxError):
                continue
        if not trees:
            return []

        imported_anywhere = self._imported_names(trees.values())

        findings: list[Finding] = []
        for path, tree in trees.items():
            assigned = self._module_constants(tree)
            if not assigned:
                continue
            read = self._loaded_names(tree)
            for name, lineno in sorted(assigned.items(), key=lambda kv: kv[1]):
                if name in read or name in imported_anywhere:
                    continue
                findings.append(
                    Finding(
                        check=self.name,
                        path=ctx.rel(path),
                        message=f"constant {name} is assigned but never read",
                        line=lineno,
                        severity=SEVERITY_FAIL,
                    )
                )
        return findings

    @staticmethod
    def _candidate_files(ctx: RepoContext) -> list[pathlib.Path]:
        candidates: list[pathlib.Path] = []
        scripts = ctx.root / "scripts"
        if scripts.is_dir():
            candidates.extend(sorted(scripts.rglob("*.py")))
        candidates.extend(sorted(ctx.root.glob("*.py")))
        return candidates

    @staticmethod
    def _module_constants(tree: ast.Module) -> dict[str, int]:
        assigned: dict[str, int] = {}
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id.isupper()
                        and target.id.isidentifier()
                    ):
                        assigned[target.id] = node.lineno
            elif isinstance(node, ast.AnnAssign):
                target = node.target
                if (
                    isinstance(target, ast.Name)
                    and target.id.isupper()
                    and target.id.isidentifier()
                ):
                    assigned[target.id] = node.lineno
        return assigned

    @staticmethod
    def _loaded_names(tree: ast.Module) -> set[str]:
        read: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                read.add(node.id)
            elif isinstance(node, ast.Attribute):
                read.add(node.attr)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                # Covers an __all__ entry.
                read.add(node.value)
        return read

    @staticmethod
    def _imported_names(trees) -> set[str]:
        names: set[str] = set()
        for tree in trees:
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        names.add(alias.asname or alias.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        names.add(alias.asname or alias.name.split(".")[0])
        return names


# ---------------------------------------------------------------------------
# 2.6 index coverage
# ---------------------------------------------------------------------------

_INDEX_ROW = re.compile(r"\[(\d{2,3}[a-z]?)\]\(\./([^/]+)/\)")


class IndexCoverageCheck:
    """Compare the example directories against the published example index.

    Two properties: every example directory is indexed, and no example is
    indexed more than once across sections. An example indexed but absent from
    the filesystem is also reported.
    """

    name = "index-coverage"
    description = "Example directories and the published index agree."

    def run(self, ctx: RepoContext) -> list[Finding]:
        index = ctx.index_path
        if not index.is_file():
            return [
                Finding(
                    check=self.name,
                    path=ctx.rel(index),
                    message="example index not found",
                    severity=SEVERITY_FAIL,
                )
            ]
        text = index.read_text(encoding="utf-8", errors="replace")
        rows = _INDEX_ROW.findall(text)

        counts: dict[str, int] = {}
        for _label, dirname in rows:
            counts[dirname] = counts.get(dirname, 0) + 1

        findings: list[Finding] = []
        on_disk = set(ctx.example_dirs)

        for name in sorted(on_disk - set(counts)):
            findings.append(
                Finding(
                    check=self.name,
                    path=ctx.rel(ctx.examples_dir / name),
                    message="example directory is not listed in the example index",
                    severity=SEVERITY_REPORT,
                )
            )
        for name in sorted(set(counts) - on_disk):
            findings.append(
                Finding(
                    check=self.name,
                    path=ctx.rel(index),
                    message=f"index lists {name!r}, which is not an example directory",
                    severity=SEVERITY_FAIL,
                )
            )
        for name, count in sorted(counts.items()):
            if count > 1 and name in on_disk:
                findings.append(
                    Finding(
                        check=self.name,
                        path=ctx.rel(index),
                        message=f"{name} is indexed in {count} sections",
                        severity=SEVERITY_REPORT,
                    )
                )
        return findings


# ---------------------------------------------------------------------------
# 2.7 contract table duplication
# ---------------------------------------------------------------------------


class ContractTableDuplicationCheck:
    """Report contract tables that exist in more than one prose document.

    Reports duplication as debt. It does not reconcile the prose -- design.md
    records retiring the duplicated tables as a separate change.
    """

    name = "contract-table-duplication"
    description = "Contract tables duplicated across documents (report-only)."

    def run(self, ctx: RepoContext) -> list[Finding]:
        presence: dict[str, list[str]] = {}
        for docname in CONTRACT_DOCUMENTS:
            path = ctx.root / docname
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for heading in CONTRACT_TABLE_HEADINGS:
                if heading in text:
                    presence.setdefault(heading, []).append(docname)

        findings: list[Finding] = []
        for heading, docs in sorted(presence.items()):
            if len(docs) > 1:
                findings.append(
                    Finding(
                        check=self.name,
                        path=", ".join(docs),
                        message=(
                            f"contract table {heading!r} appears in "
                            f"{len(docs)} documents"
                        ),
                        severity=SEVERITY_REPORT,
                    )
                )
        return findings


register(ByteCompilationCheck)
register(LicenseHeaderCheck)
register(ExampleSkeletonCheck)
register(ErrorSuppressionCheck)
register(DeadConstantCheck)
register(IndexCoverageCheck)
register(ContractTableDuplicationCheck)