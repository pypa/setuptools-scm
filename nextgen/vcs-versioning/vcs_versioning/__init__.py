"""VCS-based versioning for Python packages

Core functionality for version management based on VCS metadata.
"""

from __future__ import annotations

from ._version_cls import NonNormalizedVersion
from ._version_cls import Version
from .config import DEFAULT_LOCAL_SCHEME
from .config import DEFAULT_VERSION_SCHEME

# Public API exports
from .config import Configuration
from .scm_version import ScmVersion

__all__ = [
    "DEFAULT_LOCAL_SCHEME",
    "DEFAULT_VERSION_SCHEME",
    "Configuration",
    "NonNormalizedVersion",
    "ScmVersion",
    "Version",
]
