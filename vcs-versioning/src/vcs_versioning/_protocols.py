"""Workdir protocols for external consumers.

These protocols define the minimal surface that downstream code (version
inference, file finders, egg_info, build backends) requires from a workdir.
Backend-internal methods (node, is_dirty, describe, revsets) are not part
of the protocol.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ._scm_version import ScmVersion


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
