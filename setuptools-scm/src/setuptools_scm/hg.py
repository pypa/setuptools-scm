"""Re-export hg backend from vcs_versioning for backward compatibility

NOTE: The hg backend is private in vcs_versioning and accessed via entry points.
This module provides backward compatibility for code that imported from setuptools_scm.hg
"""

from __future__ import annotations

from vcs_versioning._backends._hg import HgWorkdir as HgWorkdir
from vcs_versioning._backends._hg import archival_to_version as archival_to_version
from vcs_versioning._backends._hg import log as log
from vcs_versioning._backends._hg import parse as parse
from vcs_versioning._backends._hg import parse_archival as parse_archival
from vcs_versioning._backends._hg import run_hg as run_hg

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
