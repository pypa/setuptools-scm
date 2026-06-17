"""Workdir protocols for external consumers and internal structuring.

External protocols define the minimal surface that downstream code (version
inference, file finders, egg_info, build backends) requires from a workdir.

Internal protocols (WorkdirState, DescribeCapable) define what the shared
git describe parser (_git_parse_inner) requires -- enabling hg-git to
satisfy the same interface without multiple inheritance.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ._run_cmd import CompletedProcess
    from ._scm_version import ScmVersion


# ---------------------------------------------------------------------------
# External consumer protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class WorkdirProtocol(Protocol):
    """What downstream consumers need from any workdir (SCM or fallback)."""

    @property
    def path(self) -> Path: ...

    def get_scm_version(self) -> ScmVersion | None:
        """Raw version metadata before overrides / formatting."""
        ...

    def list_tracked_files(self, path: Path | str = "") -> list[str]:
        """Paths to include in sdists / scm_file_list.json.

        May raise NotImplementedError when file listing is not supported
        (callers should fall back to walk_revctrl or similar).
        """
        ...


@runtime_checkable
class ScmWorkdirProtocol(WorkdirProtocol, Protocol):
    """Live VCS checkout: adds monorepo / nested-project fields."""

    @property
    def project_root(self) -> Path: ...

    @property
    def project_path(self) -> str:
        """POSIX relative path from VCS root to project_root (empty when equal)."""
        ...


# ---------------------------------------------------------------------------
# Internal protocols for git describe pipeline
# ---------------------------------------------------------------------------


class DescribeCapable(Protocol):
    """What version_from_describe() needs to produce a describe result.

    Implemented by GitWorkdir (native git describe) and GitWorkdirHgClient
    (emulated describe via hg revsets + git-mapfile).
    """

    @property
    def path(self) -> Path: ...

    @property
    def _subprocess_timeout(self) -> int | None: ...

    def default_describe(self) -> CompletedProcess: ...

    def run_git(self, args: Sequence[str]) -> CompletedProcess: ...


class WorkdirState(Protocol):
    """Post-describe enrichment: what _git_parse_inner reads after describe.

    These methods provide branch, node, dirty state, and dates used to
    enrich the ScmVersion returned by the describe pipeline.
    """

    def node(self) -> str | None: ...

    def count_all_nodes(self) -> int: ...

    def is_dirty(self) -> bool: ...

    def get_branch(self) -> str | None: ...

    def get_head_date(self) -> date | None: ...

    def get_dirty_tag_date(self) -> date | None: ...
