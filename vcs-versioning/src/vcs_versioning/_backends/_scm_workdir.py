from __future__ import annotations

import logging
from dataclasses import dataclass
from dataclasses import field as dc_field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, overload

from .._scm_version import ScmVersion

if TYPE_CHECKING:
    from .._config import Configuration


log = logging.getLogger(__name__)


class _ProjectRootDescriptor:
    """Descriptor for ``project_root`` that defaults to ``path``.

    Acts as default when no value has been set on the instance.
    Stores explicitly assigned values in the instance ``__dict__``.
    """

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    @overload
    def __get__(self, obj: None, objtype: type) -> _ProjectRootDescriptor: ...

    @overload
    def __get__(self, obj: ScmWorkdir, objtype: type | None = None) -> Path: ...

    def __get__(
        self, obj: ScmWorkdir | None, objtype: type | None = None
    ) -> Path | _ProjectRootDescriptor:
        if obj is None:
            return self
        value: Path | None = obj.__dict__.get(self._name)
        if value is None:
            return obj.path
        return value

    def __set__(self, obj: ScmWorkdir, value: Path | None) -> None:
        if isinstance(value, Path):
            obj.__dict__[self._name] = value


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
    project_root: Path = _ProjectRootDescriptor()  # type: ignore[assignment]

    _config: Configuration | None = dc_field(default=None, repr=False, compare=False)
    """Back-reference to the ``Configuration`` that discovered this workdir."""

    @property
    def _subprocess_timeout(self) -> int | None:
        """Subprocess timeout from ``config.env``.

        Returns ``None`` only when the workdir has no config at all
        (e.g. bare ``from_potential_worktree`` probes).
        """
        if self._config is None:
            return None
        return self._config.env.subprocess_timeout

    @property
    def _hg_command(self) -> str | None:
        """Hg command from ``config.env``.

        Returns ``None`` only when the workdir has no config at all
        (e.g. bare ``from_potential_worktree`` probes).
        """
        if self._config is None:
            return None
        return self._config.env.hg_command

    @property
    def project_path(self) -> str:
        """Discovered relative path from VCS root to project directory."""
        if self.path == self.project_root:
            return ""
        from .._paths import relative_project_path

        return relative_project_path(self.path, self.project_root)

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

    def get_scm_version(self) -> ScmVersion | None:
        raise NotImplementedError

    def list_tracked_files(self, path: Path | str = "") -> list[str]:
        raise NotImplementedError

    def is_file_tracked(self, path: Path) -> bool:
        raise NotImplementedError


# Backward-compat alias so existing imports keep working.
Workdir = ScmWorkdir
