# ruff: noqa: F405
"""Re-export fallbacks from vcs_versioning for backward compatibility"""

from __future__ import annotations

from vcs_versioning._fallbacks import *  # noqa: F403

__all__ = [
    "fallback_version",
    "parse_pkginfo",
]
