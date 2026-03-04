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

    # Restrict to setuptools-scm-* tags so we ignore other tags on the same
    # commit (e.g. vcs-versioning-1.0.0.dev). Must match pyproject.toml.
    import pathlib

    return get_version(
        root=pathlib.Path(__file__).parent.parent,
        version_scheme="guess-next-dev",
        local_scheme=local_scheme,
        tag_regex=r"^setuptools-scm-(?P<version>[vV]?\d+(?:\.\d+){0,2}[^\+]*)(?:\+.*)?$",
        git_describe_command=[
            "git",
            "describe",
            "--dirty",
            "--tags",
            "--long",
            "--match",
            "setuptools-scm-*",
        ],
    )


version: str = scm_version()
