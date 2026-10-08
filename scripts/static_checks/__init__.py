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

"""Static verification tier.

Asserts only properties decidable from source. Never claims an example works
at runtime. See design.md Decision 1 for the boundary between this tier and the
live tier.
"""

from .core import (  # noqa: F401
    BLOCKING_SEVERITIES,
    REPO_ROOT,
    SEVERITY_FAIL,
    SEVERITY_INFO,
    SEVERITY_REPORT,
    Check,
    Finding,
    RepoContext,
    blocking,
    discover_example_dirs,
    get,
    load_all,
    names,
    registry,
    run_checks,
)


def context_for(root=None) -> RepoContext:
    """Build a RepoContext by discovering examples from the filesystem."""
    from .core import REPO_ROOT as _DEFAULT

    root = _DEFAULT if root is None else root
    return RepoContext(root=root, example_dirs=discover_example_dirs(root))