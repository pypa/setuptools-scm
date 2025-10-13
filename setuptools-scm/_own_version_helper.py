"""
Version helper for setuptools-scm package.

This module allows setuptools-scm to use VCS metadata for its own version.
It works only if the backend-path of the build-system section from
pyproject.toml is respected.

Tag prefix configuration:
- Currently: No prefix (for backward compatibility with existing tags)
- Future: Will migrate to 'setuptools-scm-' prefix
"""

from __future__ import annotations

import os

from setuptools import build_meta as build_meta

from setuptools_scm import get_version


def scm_version() -> str:
    # Use no-local-version if SETUPTOOLS_SCM_NO_LOCAL is set (for CI uploads)
    local_scheme = (
        "no-local-version"
        if os.environ.get("SETUPTOOLS_SCM_NO_LOCAL")
        else "node-and-date"
    )

    # Note: tag_regex is currently NOT set to allow backward compatibility
    # with existing tags. To migrate to 'setuptools-scm-' prefix, uncomment:
    # tag_regex=r"^setuptools-scm-(?P<version>[vV]?\d+(?:\.\d+){0,2}[^\+]*)(?:\+.*)?$",

    # Use relative_to parent to find git root (one level up from setuptools-scm/)
    import pathlib

    return get_version(
        root=pathlib.Path(__file__).parent.parent,
        version_scheme="guess-next-dev",
        local_scheme=local_scheme,
    )


version: str = scm_version()
