"""Canonical path resolution for Configuration and discovery.

Consolidates the three places that independently compute "project directory"
and "SCM probe root" from ``relative_to`` and ``root`` into a single
``resolve_paths()`` function.
"""

from __future__ import annotations

import dataclasses
import logging
import os
import warnings
from pathlib import Path

from . import _types as _t

log = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class ResolvedPaths:
    """Canonical resolved paths for a Configuration.

    Computed once from ``relative_to`` and ``root``; consumed by config
    bridging, discovery, and workdir verification.
    """

    anchor: Path | None
    """Resolved ``relative_to`` path (file or directory), or None."""

    project_dir: Path
    """Absolute resolved directory where pyproject.toml / setup.py lives."""

    scm_probe_root: Path
    """Absolute resolved directory where SCM discovery starts."""

    project_path: str | None
    """POSIX relative path from scm_probe_root to project_dir, or None.

    ``None`` means "not computable" (e.g. root="." with no monorepo offset).
    Empty string means project_dir == scm_probe_root.
    """


def _posix_project_path(path: str) -> str:
    """Normalize a project-relative path to forward-slash form."""
    if not path:
        return path
    return Path(path).as_posix()


def resolve_paths(
    *,
    relative_to: _t.PathT | None,
    root: _t.PathT = ".",
    project_path: str | None = None,
) -> ResolvedPaths:
    """Compute canonical paths from config inputs.

    This is the single source of truth for path resolution, replacing
    duplicated logic in ``_bridge_root_to_project_path``,
    ``discover_workdir``, and ``_check_absolute_root``.
    """
    scm_probe_root = Path(_check_absolute_root(root, relative_to)).resolve()

    if relative_to is not None:
        anchor = Path(str(relative_to)).resolve()
        rel = Path(str(relative_to))
        project_dir = (rel if rel.is_dir() else rel.parent).resolve()
    else:
        anchor = None
        project_dir = scm_probe_root

    if project_path is not None:
        resolved_project_path = project_path
    elif str(root) == "." or relative_to is None:
        resolved_project_path = None
    else:
        try:
            computed = str(project_dir.relative_to(scm_probe_root))
        except ValueError:
            resolved_project_path = None
        else:
            resolved_project_path = _posix_project_path(
                "" if computed == "." else computed
            )

    return ResolvedPaths(
        anchor=anchor,
        project_dir=project_dir,
        scm_probe_root=scm_probe_root,
        project_path=resolved_project_path,
    )


def relative_project_path(scm_root: Path, project_dir: Path) -> str:
    """Compute POSIX relative path from SCM root to project directory.

    Returns empty string when they are the same directory.
    """
    if scm_root == project_dir:
        return ""
    rel = str(project_dir.relative_to(scm_root))
    return _posix_project_path("" if rel == "." else rel)


def _check_absolute_root(root: _t.PathT, relative_to: _t.PathT | None) -> str:
    """Resolve root relative to relative_to, returning an absolute path string.

    Preserves legacy warning behavior for directory relative_to and
    conflicting absolute paths.
    """
    log.debug("check absolute root=%s relative_to=%s", root, relative_to)
    if relative_to:
        if (
            os.path.isabs(root)
            and os.path.isabs(relative_to)
            and not os.path.commonpath([root, relative_to]) == root
        ):
            warnings.warn(
                f"absolute root path '{root}' overrides relative_to '{relative_to}'",
                stacklevel=3,
            )
        if os.path.isdir(relative_to):
            warnings.warn(
                "relative_to is expected to be a file,"
                f" it's the directory {relative_to}\n"
                "assuming the parent directory was passed",
                stacklevel=3,
            )
            log.debug("dir %s", relative_to)
            root = os.path.join(relative_to, root)
        else:
            log.debug("file %s", relative_to)
            root = os.path.join(os.path.dirname(relative_to), root)
    return os.path.abspath(root)
