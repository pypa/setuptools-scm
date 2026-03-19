"""Version schemes package for setuptools-scm.

This package contains all version and local schemes that determine how
version numbers are calculated and formatted from SCM metadata.
"""

from __future__ import annotations

import logging

from .. import _entrypoints
from .._scm_version import ScmVersion, callable_or_entrypoint, meta, tag_to_version
from ._common import (
    SEMVER_LEN,
    SEMVER_MINOR,
    SEMVER_PATCH,
    combine_version_with_local_parts,
)
from ._standard import (
    calver_by_date,
    date_ver_match,
    get_local_dirty_tag,
    get_local_node_and_date,
    get_local_node_and_timestamp,
    get_no_local_node,
    guess_next_date_ver,
    guess_next_dev_version,
    guess_next_simple_semver,
    guess_next_version,
    no_guess_dev_version,
    only_version,
    postrelease_version,
    release_branch_semver,
    release_branch_semver_version,
    simplified_semver_version,
)
from ._towncrier import version_from_fragments

log = logging.getLogger(__name__)

__all__ = [
    # Constants
    "SEMVER_LEN",
    "SEMVER_MINOR",
    "SEMVER_PATCH",
    # Core types and utilities
    "ScmVersion",
    "meta",
    "tag_to_version",
    "callable_or_entrypoint",
    "format_version",
    # Version schemes
    "guess_next_version",
    "guess_next_dev_version",
    "guess_next_simple_semver",
    "simplified_semver_version",
    "release_branch_semver_version",
    "release_branch_semver",  # deprecated
    "only_version",
    "no_guess_dev_version",
    "calver_by_date",
    "date_ver_match",
    "guess_next_date_ver",
    "postrelease_version",
    # Local schemes
    "get_local_node_and_date",
    "get_local_node_and_timestamp",
    "get_local_dirty_tag",
    "get_no_local_node",
    # Towncrier
    "version_from_fragments",
    # Utilities
    "combine_version_with_local_parts",
]


def format_version(version: ScmVersion) -> str:
    """Format a ScmVersion into a final version string.

    This orchestrates calling the version scheme and local scheme,
    then combining them with any local data from the original tag.

    Args:
        version: The ScmVersion to format

    Returns:
        A fully formatted version string
    """
    log.debug("scm version %s", version)
    log.debug("config %s", version.config)
    if version.preformatted:
        return str(version.tag)

    # Extract original tag's local data for later combination
    original_local = ""
    if hasattr(version.tag, "local") and version.tag.local is not None:
        original_local = str(version.tag.local)

    # Create a patched ScmVersion with only the base version (no local data) for version schemes
    from dataclasses import replace

    # Extract the base version (public part) from the tag using config's version_cls
    base_version_str = str(version.tag.public)
    base_tag = version.config.version_cls(base_version_str)
    version_for_scheme = replace(version, tag=base_tag)

    main_version = _entrypoints._call_version_scheme(
        version_for_scheme,
        "setuptools_scm.version_scheme",
        version.config.version_scheme,
    )
    log.debug("version %s", main_version)
    assert main_version is not None

    local_version = _entrypoints._call_version_scheme(
        version, "setuptools_scm.local_scheme", version.config.local_scheme, "+unknown"
    )
    log.debug("local_version %s", local_version)

    # Combine main version with original local data and new local scheme data
    return combine_version_with_local_parts(
        str(main_version), original_local, local_version
    )
