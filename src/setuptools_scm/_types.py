# ruff: noqa: F405
"""Re-export types from vcs_versioning for backward compatibility"""

from __future__ import annotations

from vcs_versioning._types import *  # noqa: F403

__all__ = [
    "CMD_TYPE",
    "SCMVERSION",
    "VERSION_SCHEME",
    "GetVersionInferenceConfig",
    "GivenPyProjectResult",
    "PathT",
]
