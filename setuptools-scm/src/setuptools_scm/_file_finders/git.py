"""Git file finder for setuptools integration.

This module provides thin wrappers that expose vcs-versioning's Git file finding
functionality to setuptools via entry points.
"""

from __future__ import annotations

from vcs_versioning import _types as _t
from vcs_versioning._file_finders._git import (
    git_archive_find_files as _git_archive_find_files,
)
from vcs_versioning._file_finders._git import git_find_files as _git_find_files


def git_find_files(path: _t.PathT = "") -> list[str]:
    """Entry point for Git file finding"""
    return _git_find_files(path)


def git_archive_find_files(path: _t.PathT = "") -> list[str]:
    """Entry point for Git archive file finding (fallback)"""
    return _git_archive_find_files(path)
