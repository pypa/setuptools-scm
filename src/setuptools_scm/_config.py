# ruff: noqa: F405
"""Re-export configuration from vcs_versioning for backward compatibility"""

from __future__ import annotations

from vcs_versioning._config import *  # noqa: F403

__all__ = [
    "DEFAULT_LOCAL_SCHEME",
    "DEFAULT_TAG_REGEX",
    "DEFAULT_VERSION_SCHEME",
    "Configuration",
    "GitConfiguration",
    "ScmConfiguration",
]
