# ruff: noqa: F405
"""Re-export entrypoints from vcs_versioning for backward compatibility"""

from __future__ import annotations

from vcs_versioning._entrypoints import *  # noqa: F403

__all__ = [
    "_get_ep",
    "entry_points",
    "im",
    "iter_entry_points",
    "version_from_entrypoint",
]
