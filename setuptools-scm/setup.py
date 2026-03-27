"""Build entry point: compute ``version`` here so it is not part of the installed package."""

from __future__ import annotations

import os
import sys

from pathlib import Path

from setuptools import setup

_root = Path(__file__).resolve().parent
sys.path.insert(0, str(_root / "src"))

from setuptools_scm import get_version
from vcs_versioning._backends._git import make_describe_command


def _package_version() -> str:
    """Resolve version using this package's tree, not the process cwd.

    ``root`` is the monorepo (``..`` relative to ``pyproject.toml``) for SCM
    discovery. ``fallback_root`` is ``.`` (the package tree) so ``PKG-INFO``
    fallbacks resolve under that directory when building from an sdist.

    ``get_version`` defaults ``fallback_root`` to ``.``; PEP 517 builds often run
    with cwd at the repo or workspace root, so fallbacks (e.g. ``PKG-INFO`` /
    ``pyproject.toml`` entry-point matching) could pick the wrong directory.
    """
    local_scheme = (
        "no-local-version"
        if os.environ.get("SETUPTOOLS_SCM_NO_LOCAL")
        else "node-and-date"
    )
    pyproject_toml = _root / "pyproject.toml"
    return get_version(
        root="..",
        relative_to=str(pyproject_toml),
        fallback_root=".",
        version_scheme="guess-next-dev",
        local_scheme=local_scheme,
        tag_regex=r"^setuptools-scm-(?P<version>v?\d+(?:\.\d+){0,2}[^\+]*)(?:\+.*)?$",
        scm={"git": {"describe_command": make_describe_command("setuptools-scm-*")}},
    )


if __name__ == "__main__":
    setup(version=_package_version())
