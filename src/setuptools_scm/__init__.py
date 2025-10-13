"""
:copyright: 2010-2023 by Ronny Pfannschmidt
:license: MIT
"""

from __future__ import annotations

from vcs_versioning import Configuration
from vcs_versioning import NonNormalizedVersion
from vcs_versioning import ScmVersion
from vcs_versioning import Version
from vcs_versioning._config import DEFAULT_LOCAL_SCHEME
from vcs_versioning._config import DEFAULT_VERSION_SCHEME
from vcs_versioning._dump_version import dump_version  # soft deprecated
from vcs_versioning._get_version_impl import _get_version

from ._get_version_impl import get_version

# Public API
__all__ = [
    "DEFAULT_LOCAL_SCHEME",
    "DEFAULT_VERSION_SCHEME",
    "Configuration",
    "NonNormalizedVersion",
    "ScmVersion",
    "Version",
    "_get_version",
    "dump_version",
    # soft deprecated imports, left for backward compatibility
    "get_version",
]
