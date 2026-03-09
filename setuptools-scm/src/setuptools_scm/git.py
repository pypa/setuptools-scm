"""Re-export git backend from vcs_versioning for backward compatibility

NOTE: The git backend is private in vcs_versioning and accessed via entry points.
This module provides backward compatibility for code that imported from setuptools_scm.git
"""

from __future__ import annotations

from vcs_versioning._backends._git import DEFAULT_DESCRIBE as DEFAULT_DESCRIBE
from vcs_versioning._backends._git import DESCRIBE_UNSUPPORTED as DESCRIBE_UNSUPPORTED
from vcs_versioning._backends._git import REF_TAG_RE as REF_TAG_RE
from vcs_versioning._backends._git import GitPreParse as GitPreParse
from vcs_versioning._backends._git import GitWorkdir as GitWorkdir
from vcs_versioning._backends._git import archival_to_version as archival_to_version
from vcs_versioning._backends._git import (
    fail_on_missing_submodules as fail_on_missing_submodules,
)
from vcs_versioning._backends._git import fail_on_shallow as fail_on_shallow
from vcs_versioning._backends._git import fetch_on_shallow as fetch_on_shallow
from vcs_versioning._backends._git import get_working_directory as get_working_directory
from vcs_versioning._backends._git import log as log
from vcs_versioning._backends._git import parse as parse
from vcs_versioning._backends._git import parse_archival as parse_archival
from vcs_versioning._backends._git import run_git as run_git
from vcs_versioning._backends._git import version_from_describe as version_from_describe
from vcs_versioning._backends._git import warn_on_shallow as warn_on_shallow

__all__ = [
    # Constants
    "DEFAULT_DESCRIBE",
    "DESCRIBE_UNSUPPORTED",
    "REF_TAG_RE",
    # Classes
    "GitPreParse",
    "GitWorkdir",
    # Functions
    "archival_to_version",
    "fail_on_missing_submodules",
    "fail_on_shallow",
    "fetch_on_shallow",
    "get_working_directory",
    "log",
    "parse",
    "parse_archival",
    "run_git",
    "version_from_describe",
    "warn_on_shallow",
]
