"""Re-export fallbacks from vcs_versioning for backward compatibility"""

from __future__ import annotations

from vcs_versioning._fallbacks import fallback_version as fallback_version
from vcs_versioning._fallbacks import log as log
from vcs_versioning._fallbacks import parse_pkginfo as parse_pkginfo

__all__ = [
    # Functions
    "fallback_version",
    "log",
    "parse_pkginfo",
]
