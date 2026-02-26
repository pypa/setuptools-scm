"""Re-export integration from vcs_versioning for backward compatibility"""

from __future__ import annotations

from vcs_versioning._integration import data_from_mime as data_from_mime
from vcs_versioning._integration import log as log

__all__ = [
    # Functions
    "data_from_mime",
    "log",
]
