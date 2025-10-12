# ruff: noqa: F405
"""Re-export discover from vcs_versioning for backward compatibility"""

from __future__ import annotations

from vcs_versioning._discover import *  # noqa: F403

__all__ = [
    "iter_matching_entrypoints",
    "match_entrypoint",
    "walk_potential_roots",
]
