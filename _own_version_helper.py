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

import logging
import os
import sys

from collections.abc import Callable

from setuptools import build_meta as build_meta
from vcs_versioning import _types as _t

from setuptools_scm import Configuration
from setuptools_scm import get_version
from setuptools_scm import git
from setuptools_scm import hg
from setuptools_scm.fallbacks import parse_pkginfo
from setuptools_scm.version import ScmVersion
from setuptools_scm.version import get_local_node_and_date
from setuptools_scm.version import get_no_local_node
from setuptools_scm.version import guess_next_dev_version

log = logging.getLogger("setuptools_scm")
# todo: take fake entrypoints from pyproject.toml
try_parse: list[Callable[[_t.PathT, Configuration], ScmVersion | None]] = [
    parse_pkginfo,
    git.parse,
    hg.parse,
    git.parse_archival,
    hg.parse_archival,
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


def scm_version() -> str:
    # Use no-local-version if SETUPTOOLS_SCM_NO_LOCAL is set (for CI uploads)
    local_scheme = (
        get_no_local_node
        if os.environ.get("SETUPTOOLS_SCM_NO_LOCAL")
        else get_local_node_and_date
    )

    # Note: tag_regex is currently NOT set to allow backward compatibility
    # with existing tags. To migrate to 'setuptools-scm-' prefix, uncomment:
    # tag_regex=r"^setuptools-scm-(?P<version>[vV]?\d+(?:\.\d+){0,2}[^\+]*)(?:\+.*)?$",
    return get_version(
        relative_to=__file__,
        parse=parse,
        version_scheme=guess_next_dev_version,
        local_scheme=local_scheme,
    )


version: str
print("__file__", __file__, file=sys.stderr)


def __getattr__(name: str) -> str:
    if name == "version":
        global version
        version = scm_version()
        return version
    raise AttributeError(name)
