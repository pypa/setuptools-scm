"""Re-export hg backend from vcs_versioning for backward compatibility

NOTE: The hg backend is private in vcs_versioning and accessed via entry points.
This module provides backward compatibility for code that imported from setuptools_scm.hg
"""

from __future__ import annotations

from vcs_versioning import _config
from vcs_versioning import _scm_version
from vcs_versioning._backends._hg import HgWorkdir as _CoreHgWorkdir
from vcs_versioning._backends._hg import archival_to_version as archival_to_version
from vcs_versioning._backends._hg import log as log
from vcs_versioning._backends._hg import parse as parse
from vcs_versioning._backends._hg import parse_archival as parse_archival
from vcs_versioning._backends._hg import run_hg as run_hg


class HgWorkdir(_CoreHgWorkdir):
    """Backward-compatible shim accepting optional config parameter."""

    def get_scm_version(
        self, config: _config.Configuration | None = None
    ) -> _scm_version.ScmVersion | None:
        from ._compat_helpers import _bind_config

        with _bind_config(self, config):
            return super().get_scm_version()


__all__ = [
    # Classes
    "HgWorkdir",
    # Functions
    "archival_to_version",
    "log",
    "parse",
    "parse_archival",
    "run_hg",
]
