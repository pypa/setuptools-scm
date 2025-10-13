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

from vcs_versioning import Configuration
from vcs_versioning import _types as _t
from vcs_versioning._backends import _git as git
from vcs_versioning._backends import _hg as hg
from vcs_versioning._fallbacks import fallback_version
from vcs_versioning._fallbacks import parse_pkginfo
from vcs_versioning._get_version_impl import get_version
from vcs_versioning._version_schemes import ScmVersion
from vcs_versioning._version_schemes import get_local_node_and_date
from vcs_versioning._version_schemes import get_no_local_node
from vcs_versioning._version_schemes import guess_next_dev_version

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

    # __file__ is nextgen/vcs-versioning/_own_version_helper.py
    # pyproject.toml is in nextgen/vcs-versioning/pyproject.toml
    pyproject_path = os.path.join(os.path.dirname(__file__), "pyproject.toml")

    # root is the git repo root (../..)
    # fallback_root is the vcs-versioning package dir (.)
    # relative_to anchors to pyproject.toml
    # fallback_version is used when no vcs-versioning- tags exist yet
    return get_version(
        root="../..",
        fallback_root=".",
        relative_to=pyproject_path,
        parse=parse,
        version_scheme=guess_next_dev_version,
        local_scheme=local_scheme,
        tag_regex=r"^vcs-versioning-(?P<version>[vV]?\d+(?:\.\d+){0,2}[^\+]*)(?:\+.*)?$",
        git_describe_command="git describe --dirty --tags --long --match 'vcs-versioning-*'",
        fallback_version="0.1.1+pre.tag",
    )


__version__: str = _get_version()
