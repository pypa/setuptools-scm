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
    local_scheme = (
        "no-local-version"
        if os.environ.get("SETUPTOOLS_SCM_NO_LOCAL")
        else "node-and-date"
    )
    return get_version(
        root=_root.parent,
        version_scheme="guess-next-dev",
        local_scheme=local_scheme,
        tag_regex=r"^setuptools-scm-(?P<version>v?\d+(?:\.\d+){0,2}[^\+]*)(?:\+.*)?$",
        scm={"git": {"describe_command": make_describe_command("setuptools-scm-*")}},
    )


if __name__ == "__main__":
    setup(version=_package_version())
