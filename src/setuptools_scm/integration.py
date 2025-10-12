# ruff: noqa: F405
"""Re-export integration from vcs_versioning for backward compatibility"""

from __future__ import annotations

from vcs_versioning._integration import *  # noqa: F403

__all__ = [
    "data_from_mime",
]
