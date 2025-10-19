"""VCS-based versioning for Python packages

Core functionality for version management based on VCS metadata.
"""

from __future__ import annotations

# Public API exports
from ._config import DEFAULT_LOCAL_SCHEME, DEFAULT_VERSION_SCHEME, Configuration
from ._version_cls import NonNormalizedVersion, Version
from ._version_inference import infer_version_string
from ._version_schemes import ScmVersion

__all__ = [
    "DEFAULT_LOCAL_SCHEME",
    "DEFAULT_VERSION_SCHEME",
    "Configuration",
    "NonNormalizedVersion",
    "ScmVersion",
    "Version",
    "infer_version_string",
]
