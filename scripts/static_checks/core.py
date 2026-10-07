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

"""Core types for the static verification tier.

The static tier asserts only properties that are decidable from source. It
never claims an example works at runtime -- see design.md Decision 1. It runs
with no gateway and no SDK installed, so it depends on the standard library
only.

A finding carries a severity that says how it affects the tier's exit status:

    fail    the tier fails while this finding is present
    report  the finding is surfaced but does not fail the tier
    info    advisory output only, never affects the exit status
"""

from __future__ import annotations

import dataclasses
import pathlib
from collections.abc import Callable, Iterable
from typing import Protocol

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLES_DIRNAME = "examples"
EXAMPLE_INDEX_RELPATH = "examples/README.md"

SEVERITY_FAIL = "fail"
SEVERITY_REPORT = "report"
SEVERITY_INFO = "info"

#: Severities that make the tier's exit status non-zero.
BLOCKING_SEVERITIES = frozenset({SEVERITY_FAIL})


@dataclasses.dataclass(frozen=True)
class Finding:
    """One reported property violation or observation."""

    check: str
    path: str
    message: str
    severity: str = SEVERITY_REPORT
    line: int | None = None

    def __str__(self) -> str:
        location = f"{self.path}:{self.line}" if self.line else self.path
        return f"[{self.severity}] {self.check}: {location}: {self.message}"


@dataclasses.dataclass(frozen=True)
class RepoContext:
    """Everything a check is allowed to look at.

    Checks receive this rather than reaching for module-level globals so that a
    test can point a check at a fixture tree instead of the real repository.
    """

    root: pathlib.Path
    example_dirs: tuple[str, ...]

    @property
    def examples_dir(self) -> pathlib.Path:
        return self.root / EXAMPLES_DIRNAME

    @property
    def index_path(self) -> pathlib.Path:
        return self.root / EXAMPLE_INDEX_RELPATH

    def rel(self, path: pathlib.Path) -> str:
        try:
            return str(path.relative_to(self.root))
        except ValueError:
            return str(path)

    def python_files(self) -> list[pathlib.Path]:
        """Every Python file under the example directories, sorted."""
        found: list[pathlib.Path] = []
        for name in self.example_dirs:
            found.extend(sorted((self.examples_dir / name).rglob("*.py")))
        return found


def discover_example_dirs(root: pathlib.Path) -> tuple[str, ...]:
    """Enumerate example directories from the filesystem.

    This is the only source of the example set (design.md Decision 4). A
    directory counts as an example when its name starts with a digit, matching
    the numbering convention the examples are published under.
    """
    examples = root / EXAMPLES_DIRNAME
    if not examples.is_dir():
        return ()
    return tuple(
        sorted(
            (d.name for d in examples.iterdir() if d.is_dir() and d.name[:1].isdigit()),
            key=_example_sort_key,
        )
    )


def _example_sort_key(name: str) -> tuple[int, int, str]:
    """Sort ``45b_ticker_handler`` before ``46_...``, not after ``127_...``.

    Plain string ordering puts the three-digit 100..127 block ahead of 10..45,
    which is the ordering defect the live runner had. Splitting the numeric
    prefix from any suffix keeps the run order matching the numbering scheme.
    """
    digits = ""
    for ch in name:
        if ch.isdigit():
            digits += ch
        else:
            break
    suffix = name[len(digits):]
    if digits.isdigit():
        number = int(digits)
    else:
        number = -1
    # A letter suffix sorts immediately after its own number, before the next.
    return (number, 0 if not suffix else 1, suffix)


class Check(Protocol):
    """A single static property check."""

    name: str
    description: str

    def run(self, ctx: RepoContext) -> Iterable[Finding]:  # pragma: no cover
        ...


CheckFactory = Callable[[], Check]

_REGISTRY: dict[str, CheckFactory] = {}


def register(factory: CheckFactory) -> CheckFactory:
    """Register a check factory. Usable as a decorator."""
    instance = factory()
    _REGISTRY[instance.name] = factory
    return factory


def registry() -> dict[str, CheckFactory]:
    return dict(_REGISTRY)


def get(name: str) -> Check:
    return _REGISTRY[name]()


def names() -> list[str]:
    return sorted(_REGISTRY)


def load_all() -> None:
    """Import the module that defines the checks, populating the registry."""
    from . import checks  # noqa: F401  (import registers)


def run_checks(
    ctx: RepoContext, selected: Iterable[str] | None = None
) -> list[Finding]:
    """Run the selected checks and return every finding, unsorted."""
    load_all()
    chosen = list(selected) if selected is not None else names()
    findings: list[Finding] = []
    for name in chosen:
        findings.extend(get(name).run(ctx))
    return findings


def blocking(findings: Iterable[Finding]) -> list[Finding]:
    return [f for f in findings if f.severity in BLOCKING_SEVERITIES]