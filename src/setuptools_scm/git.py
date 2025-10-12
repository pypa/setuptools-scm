# ruff: noqa: F405
"""Re-export git backend from vcs_versioning for backward compatibility

NOTE: The git backend is private in vcs_versioning and accessed via entry points.
This module provides backward compatibility for code that imported from setuptools_scm.git
"""

from __future__ import annotations

from vcs_versioning._backends._git import *  # noqa: F403

__all__ = [
    "GitPreParse",
    "GitWorkdir",
    "parse",
    "parse_archival",
]
