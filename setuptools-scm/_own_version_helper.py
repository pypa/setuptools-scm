"""
Version helper for setuptools-scm package.

This module allows setuptools-scm to use VCS metadata for its own version.
It works only if the backend-path of the build-system section from
pyproject.toml is respected.

Version tags must carry the ``setuptools-scm-`` prefix (e.g.
``setuptools-scm-v10.0.0``).  The tag regex and git describe ``--match``
pattern are both restricted to this prefix so that co-located
``vcs-versioning-*`` tags on the same commit do not affect the result.
"""

from __future__ import annotations

import os

from pathlib import Path

from setuptools import build_meta as build_meta
from vcs_versioning._backends._git import make_describe_command

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
    return get_version(
        root=Path(__file__).parent.parent,
        version_scheme="guess-next-dev",
        local_scheme=local_scheme,
        tag_regex=r"^setuptools-scm-(?P<version>v?\d+(?:\.\d+){0,2}[^\+]*)(?:\+.*)?$",
        scm={"git": {"describe_command": make_describe_command("setuptools-scm-*")}},
    )


version: str = scm_version()
