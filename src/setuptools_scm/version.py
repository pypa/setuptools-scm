# ruff: noqa: F405
"""Re-export version schemes from vcs_versioning for backward compatibility"""

from __future__ import annotations

from vcs_versioning._version_schemes import *  # noqa: F403

__all__ = [
    "ScmVersion",
    "calver_by_date",
    "format_version",
    "get_local_dirty_tag",
    "get_local_node_and_date",
    "get_local_node_and_timestamp",
    "get_no_local_node",
    "guess_next_dev_version",
    "guess_next_version",
    "meta",
    "no_guess_dev_version",
    "only_version",
    "postrelease_version",
    "release_branch_semver_version",
    "simplified_semver_version",
    "tag_to_version",
]
