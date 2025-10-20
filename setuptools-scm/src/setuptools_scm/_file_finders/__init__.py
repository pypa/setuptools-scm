"""Setuptools file finder entry point.

This module provides the setuptools.file_finders entry point that integrates
vcs-versioning's file finding capabilities with setuptools.

The core file finding logic has been moved to vcs-versioning._file_finders
to allow standalone usage without setuptools dependency.
"""

from __future__ import annotations

from vcs_versioning import _types as _t
from vcs_versioning._file_finders import find_files as _find_files


def find_files(path: _t.PathT = "") -> list[str]:
    """Setuptools file finder entry point.

    This is the entry point registered as 'setuptools.file_finders'
    and is called by setuptools during sdist creation.
    """
    return _find_files(path)
