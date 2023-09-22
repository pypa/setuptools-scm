"""
:copyright: 2010-2023 by Ronny Pfannschmidt
:license: MIT
"""
from __future__ import annotations

from ._config import Configuration
from ._config import DEFAULT_LOCAL_SCHEME  # soft deprecated
from ._config import DEFAULT_VERSION_SCHEME  # soft deprecated
from ._get_version_impl import _get_version  # soft deprecated
from ._get_version_impl import get_version  # soft deprecated
from ._integration.dump_version import dump_version  # soft deprecated
from ._version_cls import NonNormalizedVersion
from ._version_cls import Version
from .version import ScmVersion


# Public API
__all__ = [
    # soft deprecated imports, left for backward compatibility
    "get_version",
    "_get_version",
    "dump_version",
    "DEFAULT_VERSION_SCHEME",
    "DEFAULT_LOCAL_SCHEME",
    "Configuration",
    "Version",
    "ScmVersion",
    "NonNormalizedVersion",
]
