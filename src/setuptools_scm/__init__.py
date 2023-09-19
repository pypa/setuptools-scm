"""
:copyright: 2010-2023 by Ronny Pfannschmidt
:license: MIT
"""
from __future__ import annotations

from ._config import Configuration
from ._get_version_impl import _get_version  # soft deprecated
from ._get_version_impl import get_version  # soft deprecated
from ._integration.dump_version import dump_version  # soft deprecated
from ._version_cls import NonNormalizedVersion
from ._version_cls import Version
from .version import ScmVersion


# Public API
__all__ = [
    "get_version",  # deprecated imported for backward compatibility
    "_get_version",  # deprecated imported for backward compatibility
    "dump_version",  # deprecated imported for backward compatibility
    "Configuration",
    "Version",
    "ScmVersion",
    "NonNormalizedVersion",
]
