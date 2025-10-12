# ruff: noqa: F405
"""Re-export version classes from vcs_versioning for backward compatibility"""

from __future__ import annotations

from vcs_versioning._version_cls import *  # noqa: F403
from vcs_versioning._version_cls import _validate_version_cls
from vcs_versioning._version_cls import _version_as_tuple

__all__ = [
    "NonNormalizedVersion",
    "Version",
    "_validate_version_cls",
    "_version_as_tuple",
]
