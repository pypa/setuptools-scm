"""Re-export hg_git from vcs_versioning for backward compatibility

NOTE: The hg_git module is private in vcs_versioning.
This module provides backward compatibility for code that imported from setuptools_scm.hg_git
"""

from __future__ import annotations

from vcs_versioning import _config
from vcs_versioning import _scm_version
from vcs_versioning._backends._hg_git import (
    GitWorkdirHgClient as _CoreGitWorkdirHgClient,
)
from vcs_versioning._backends._hg_git import log as log


class GitWorkdirHgClient(_CoreGitWorkdirHgClient):
    """Backward-compatible shim accepting optional config parameter."""

    def get_scm_version(
        self, config: _config.Configuration | None = None
    ) -> _scm_version.ScmVersion | None:
        from ._compat_helpers import _bind_config

        with _bind_config(self, config):
            return super().get_scm_version()


__all__ = [
    # Classes
    "GitWorkdirHgClient",
    "log",
]
