# ruff: noqa: F405
"""Re-export hg backend from vcs_versioning for backward compatibility

NOTE: The hg backend is private in vcs_versioning and accessed via entry points.
This module provides backward compatibility for code that imported from setuptools_scm.hg
"""

from __future__ import annotations

from vcs_versioning._backends._hg import *  # noqa: F403

__all__ = [
    "HgWorkdir",
    "parse",
    "parse_archival",
]
