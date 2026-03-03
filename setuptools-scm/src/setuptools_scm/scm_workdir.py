"""Re-export scm_workdir from vcs_versioning for backward compatibility

NOTE: The scm_workdir module is private in vcs_versioning.
This module provides backward compatibility for code that imported from setuptools_scm.scm_workdir
"""

from __future__ import annotations

from vcs_versioning._backends._scm_workdir import Workdir as Workdir
from vcs_versioning._backends._scm_workdir import (
    get_latest_file_mtime as get_latest_file_mtime,
)
from vcs_versioning._backends._scm_workdir import log as log

__all__ = [
    # Classes
    "Workdir",
    # Functions
    "get_latest_file_mtime",
    "log",
]
