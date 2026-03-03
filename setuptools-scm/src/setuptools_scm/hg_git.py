"""Re-export hg_git from vcs_versioning for backward compatibility

NOTE: The hg_git module is private in vcs_versioning.
This module provides backward compatibility for code that imported from setuptools_scm.hg_git
"""

from __future__ import annotations

from vcs_versioning._backends._hg_git import GitWorkdirHgClient as GitWorkdirHgClient
from vcs_versioning._backends._hg_git import log as log

__all__ = [
    # Classes
    "GitWorkdirHgClient",
    "log",
]
