"""Re-export version schemes from vcs_versioning for backward compatibility"""

from __future__ import annotations

from vcs_versioning._version_schemes import SEMVER_LEN as SEMVER_LEN
from vcs_versioning._version_schemes import SEMVER_MINOR as SEMVER_MINOR
from vcs_versioning._version_schemes import SEMVER_PATCH as SEMVER_PATCH
from vcs_versioning._version_schemes import ScmVersion as ScmVersion
from vcs_versioning._version_schemes import (
    callable_or_entrypoint as callable_or_entrypoint,
)
from vcs_versioning._version_schemes import calver_by_date as calver_by_date
from vcs_versioning._version_schemes import date_ver_match as date_ver_match
from vcs_versioning._version_schemes import format_version as format_version
from vcs_versioning._version_schemes import get_local_dirty_tag as get_local_dirty_tag
from vcs_versioning._version_schemes import (
    get_local_node_and_date as get_local_node_and_date,
)
from vcs_versioning._version_schemes import (
    get_local_node_and_timestamp as get_local_node_and_timestamp,
)
from vcs_versioning._version_schemes import get_no_local_node as get_no_local_node
from vcs_versioning._version_schemes import guess_next_date_ver as guess_next_date_ver
from vcs_versioning._version_schemes import (
    guess_next_dev_version as guess_next_dev_version,
)
from vcs_versioning._version_schemes import (
    guess_next_simple_semver as guess_next_simple_semver,
)
from vcs_versioning._version_schemes import guess_next_version as guess_next_version
from vcs_versioning._version_schemes import log as log
from vcs_versioning._version_schemes import meta as meta
from vcs_versioning._version_schemes import no_guess_dev_version as no_guess_dev_version
from vcs_versioning._version_schemes import only_version as only_version
from vcs_versioning._version_schemes import postrelease_version as postrelease_version
from vcs_versioning._version_schemes import (
    release_branch_semver as release_branch_semver,
)
from vcs_versioning._version_schemes import (
    release_branch_semver_version as release_branch_semver_version,
)
from vcs_versioning._version_schemes import (
    simplified_semver_version as simplified_semver_version,
)
from vcs_versioning._version_schemes import tag_to_version as tag_to_version

__all__ = [
    # Constants
    "SEMVER_LEN",
    "SEMVER_MINOR",
    "SEMVER_PATCH",
    # Classes
    "ScmVersion",
    # Functions
    "callable_or_entrypoint",
    "calver_by_date",
    "date_ver_match",
    "format_version",
    "get_local_dirty_tag",
    "get_local_node_and_date",
    "get_local_node_and_timestamp",
    "get_no_local_node",
    "guess_next_date_ver",
    "guess_next_dev_version",
    "guess_next_simple_semver",
    "guess_next_version",
    "log",
    "meta",
    "no_guess_dev_version",
    "only_version",
    "postrelease_version",
    "release_branch_semver",
    "release_branch_semver_version",
    "simplified_semver_version",
    "tag_to_version",
]
