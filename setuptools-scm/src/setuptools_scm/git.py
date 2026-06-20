"""Re-export git backend from vcs_versioning for backward compatibility

NOTE: The git backend is private in vcs_versioning and accessed via entry points.
This module provides backward compatibility for code that imported from setuptools_scm.git
"""

from __future__ import annotations

from vcs_versioning import _config
from vcs_versioning import _scm_version
from vcs_versioning._backends._git import DEFAULT_DESCRIBE as DEFAULT_DESCRIBE
from vcs_versioning._backends._git import DESCRIBE_UNSUPPORTED as DESCRIBE_UNSUPPORTED
from vcs_versioning._backends._git import REF_TAG_RE as REF_TAG_RE
from vcs_versioning._backends._git import GitPreParse as GitPreParse
from vcs_versioning._backends._git import GitWorkdir as _CoreGitWorkdir
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


class GitWorkdir(_CoreGitWorkdir):
    """Backward-compatible shim accepting optional config parameter."""

    def get_scm_version(
        self, config: _config.Configuration | None = None
    ) -> _scm_version.ScmVersion | None:
        from ._compat_helpers import _bind_config

        with _bind_config(self, config):
            return super().get_scm_version()

    def run_describe(
        self, config: _config.Configuration | None = None
    ) -> _scm_version.ScmVersion:
        from ._compat_helpers import _bind_config

        with _bind_config(self, config):
            version = super().get_scm_version()
        if version is None:
            raise LookupError(f"no version could be determined from {self.path}")
        return version


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
