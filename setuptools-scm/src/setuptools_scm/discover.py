"""Re-export discover from vcs_versioning for backward compatibility"""

from __future__ import annotations

from vcs_versioning._discover import (
    iter_matching_entrypoints as iter_matching_entrypoints,
)
from vcs_versioning._discover import log as log
from vcs_versioning._discover import match_entrypoint as match_entrypoint
from vcs_versioning._discover import walk_potential_roots as walk_potential_roots

__all__ = [
    # Functions
    "iter_matching_entrypoints",
    "log",
    "match_entrypoint",
    "walk_potential_roots",
]
