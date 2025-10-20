"""Mercurial file finder for setuptools integration.

This module provides thin wrappers that expose vcs-versioning's Mercurial file finding
functionality to setuptools via entry points.
"""

from __future__ import annotations

from vcs_versioning import _types as _t
from vcs_versioning._file_finders._hg import (
    hg_archive_find_files as _hg_archive_find_files,
)
from vcs_versioning._file_finders._hg import hg_find_files as _hg_find_files


def hg_find_files(path: str = "") -> list[str]:
    """Entry point for Mercurial file finding"""
    return _hg_find_files(path)


def hg_archive_find_files(path: _t.PathT = "") -> list[str]:
    """Entry point for Mercurial archive file finding (fallback)"""
    return _hg_archive_find_files(path)
