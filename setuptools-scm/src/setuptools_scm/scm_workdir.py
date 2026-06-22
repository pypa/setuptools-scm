"""Re-export scm_workdir from vcs_versioning for backward compatibility

NOTE: The scm_workdir module is private in vcs_versioning.
This module provides backward compatibility for code that imported from setuptools_scm.scm_workdir
"""

from __future__ import annotations

from vcs_versioning import _config
from vcs_versioning import _scm_version
from vcs_versioning._backends._scm_workdir import ScmWorkdir as _CoreScmWorkdir
from vcs_versioning._backends._scm_workdir import (
    get_latest_file_mtime as get_latest_file_mtime,
)
from vcs_versioning._backends._scm_workdir import log as log


class ScmWorkdir(_CoreScmWorkdir):
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


Workdir = ScmWorkdir

__all__ = [
    # Classes
    "ScmWorkdir",
    "Workdir",
    # Functions
    "get_latest_file_mtime",
    "log",
]
