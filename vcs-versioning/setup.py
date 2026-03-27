"""Build entry point: compute ``version`` here so it is not part of the installed package."""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Callable
from pathlib import Path

from setuptools import setup

_root = Path(__file__).resolve().parent
sys.path.insert(0, str(_root / "src"))

from vcs_versioning import Configuration
from vcs_versioning import _types as _t
from vcs_versioning._backends import _git as git
from vcs_versioning._backends import _hg as hg
from vcs_versioning._fallbacks import fallback_version, parse_pkginfo
from vcs_versioning._get_version_impl import get_version, resolved_fallback_root
from vcs_versioning._version_schemes import (
    ScmVersion,
    get_local_node_and_date,
    get_no_local_node,
    guess_next_dev_version,
)

log = logging.getLogger("vcs_versioning")

_try_parse: list[Callable[[_t.PathT, Configuration], ScmVersion | None]] = [
    parse_pkginfo,
    git.parse,
    hg.parse,
    git.parse_archival,
    hg.parse_archival,
    fallback_version,
]


def _parse(root: str, config: Configuration) -> ScmVersion | None:
    for maybe_parse in _try_parse:
        try:
            parse_root = (
                resolved_fallback_root(config) if maybe_parse is parse_pkginfo else root
            )
            parsed = maybe_parse(parse_root, config)
        except OSError as e:
            log.warning("parse with %s failed with: %s", maybe_parse, e)
        else:
            if parsed is not None:
                return parsed
    return None


def _package_version() -> str:
    """Version from VCS with ``vcs-versioning-`` tag prefix.

    ``root`` is the monorepo (``..`` relative to ``pyproject.toml``) for SCM
    discovery. ``fallback_root`` is ``.`` (the package tree next to
    ``pyproject.toml``) so ``PKG-INFO`` from an sdist is read from the right
    place (see ``_parse`` / ``_pkginfo_root``).
    """
    local_scheme = (
        get_no_local_node
        if os.environ.get("VCS_VERSIONING_NO_LOCAL")
        else get_local_node_and_date
    )
    _pyproject_path = _root / "pyproject.toml"

    return get_version(
        root="..",
        fallback_root=".",
        relative_to=str(_pyproject_path),
        parse=_parse,
        version_scheme=guess_next_dev_version,
        local_scheme=local_scheme,
        tag_regex=r"^vcs-versioning-(?P<version>v?\d+(?:\.\d+){0,2}[^\+]*)(?:\+.*)?$",
        scm={
            "git": {"describe_command": git.make_describe_command("vcs-versioning-*")}
        },
        fallback_version="0.1.1+pre.tag",
    )


if __name__ == "__main__":
    setup(version=_package_version())
