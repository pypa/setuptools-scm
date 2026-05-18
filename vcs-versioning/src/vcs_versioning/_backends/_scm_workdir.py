from __future__ import annotations

import logging
from dataclasses import dataclass
from dataclasses import field as dc_field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, cast

from .._scm_version import ScmVersion

if TYPE_CHECKING:
    from .._config import Configuration
    from .._environment import VcsEnvironment

log = logging.getLogger(__name__)


def get_latest_file_mtime(changed_files: list[str], base_path: Path) -> date | None:
    """Get the latest modification time of the given files.

    Args:
        changed_files: List of relative file paths
        base_path: Base directory path to resolve relative paths

    Returns:
        The date of the most recently modified file, or None if no valid files found
    """
    if not changed_files or changed_files == [""]:
        return None

    latest_mtime = 0.0
    for filepath in changed_files:
        full_path = base_path / filepath
        try:
            file_stat = full_path.stat()
            latest_mtime = max(latest_mtime, file_stat.st_mtime)
        except OSError:
            log.debug("Failed to get mtime for %s", full_path)
            continue

    if latest_mtime > 0:
        dt = datetime.fromtimestamp(latest_mtime, timezone.utc)
        return dt.date()

    return None


@dataclass()
class ScmWorkdir:
    """Base class for VCS work directories.

    Two absolute paths model the duality of a project within a VCS checkout:
    ``path`` is the VCS root (where .git/.hg lives) and ``project_root`` is
    the project directory (where pyproject.toml lives).  For top-level projects
    the two are identical.

    The optional ``_config`` reference is set by ``discover_workdir`` so that
    methods like ``is_dirty`` and ``node`` can read runtime settings
    (subprocess timeout, hg command) from ``config._env`` without a ContextVar.
    """

    path: Path
    project_root: Path | None = dc_field(default=None)

    _config: Configuration | None = dc_field(default=None, repr=False, compare=False)
    """Back-reference to the ``Configuration`` that discovered this workdir."""

    def __post_init__(self) -> None:
        if self.project_root is None:
            self.project_root = self.path

    @property
    def _subprocess_timeout(self) -> int | None:
        """Subprocess timeout from ``config.env``.

        Returns ``None`` only when the workdir has no config at all
        (e.g. bare ``from_potential_worktree`` probes).
        """
        if self._config is None:
            return None
        env = cast("VcsEnvironment", self._config.env)
        return env.subprocess_timeout

    @property
    def _hg_command(self) -> str | None:
        """Hg command from ``config.env``.

        Returns ``None`` only when the workdir has no config at all
        (e.g. bare ``from_potential_worktree`` probes).
        """
        if self._config is None:
            return None
        env = cast("VcsEnvironment", self._config.env)
        return env.hg_command

    @property
    def project_path(self) -> str:
        """Discovered relative path from VCS root to project directory."""
        assert self.project_root is not None
        if self.path == self.project_root:
            return ""
        return str(self.project_root.relative_to(self.path))

    @property
    def config(self) -> Configuration:
        """The ``Configuration`` that discovered this workdir."""
        if self._config is None:
            raise RuntimeError(
                f"{type(self).__name__} has no associated Configuration. "
                "Use Configuration.discover_workdir() to obtain a properly "
                "configured workdir, or set workdir._config = config explicitly."
            )
        return self._config

    def run_describe(self) -> ScmVersion:
        raise NotImplementedError(self.run_describe)

    def get_scm_version(self) -> ScmVersion | None:
        raise NotImplementedError

    def list_tracked_files(self, path: Path | str = "") -> list[str]:
        raise NotImplementedError

    def is_file_tracked(self, path: Path) -> bool:
        raise NotImplementedError


# Backward-compat alias so existing imports keep working.
Workdir = ScmWorkdir
