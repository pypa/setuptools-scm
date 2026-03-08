"""
Version helper for vcs-versioning package.

This module allows vcs-versioning to use VCS metadata for its own version,
with the tag prefix 'vcs-versioning-'.

Used by hatchling's code version source.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from pathlib import Path

from vcs_versioning import Configuration
from vcs_versioning import _types as _t
from vcs_versioning._backends import _git as git
from vcs_versioning._backends import _hg as hg
from vcs_versioning._fallbacks import fallback_version, parse_pkginfo
from vcs_versioning._get_version_impl import get_version
from vcs_versioning._version_schemes import (
    ScmVersion,
    get_local_node_and_date,
    get_no_local_node,
    guess_next_dev_version,
)

log = logging.getLogger("vcs_versioning")

# Try these parsers in order for vcs-versioning's own version
try_parse: list[Callable[[_t.PathT, Configuration], ScmVersion | None]] = [
    parse_pkginfo,
    git.parse,
    hg.parse,
    git.parse_archival,
    hg.parse_archival,
    fallback_version,  # Last resort: use fallback_version from config
]


def parse(root: str, config: Configuration) -> ScmVersion | None:
    for maybe_parse in try_parse:
        try:
            parsed = maybe_parse(root, config)
        except OSError as e:
            log.warning("parse with %s failed with: %s", maybe_parse, e)
        else:
            if parsed is not None:
                return parsed
    return None


def _get_version() -> str:
    """Get version from VCS with vcs-versioning- tag prefix."""
    # Use no-local-version if VCS_VERSIONING_NO_LOCAL is set (for CI uploads)
    local_scheme = (
        get_no_local_node
        if os.environ.get("VCS_VERSIONING_NO_LOCAL")
        else get_local_node_and_date
    )

    # Resolve repo root from this file's location so version detection works
    # regardless of cwd (e.g. when uv build runs from workspace root).
    _here = Path(__file__).resolve()
    _repo_root = _here.parent.parent
    _pyproject_path = _here.parent / "pyproject.toml"

    return get_version(
        root=str(_repo_root),
        fallback_root=str(_here.parent),
        relative_to=str(_pyproject_path),
        parse=parse,
        version_scheme=guess_next_dev_version,
        local_scheme=local_scheme,
        tag_regex=r"^vcs-versioning-(?P<version>v?\d+(?:\.\d+){0,2}[^\+]*)(?:\+.*)?$",
        scm={
            "git": {"describe_command": git.make_describe_command("vcs-versioning-*")}
        },
        fallback_version="0.1.1+pre.tag",
    )


__version__: str = _get_version()
