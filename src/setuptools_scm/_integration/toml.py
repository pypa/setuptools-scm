# ruff: noqa: F405
"""Re-export toml utilities from vcs_versioning for backward compatibility"""

from __future__ import annotations

from vcs_versioning._toml import *  # noqa: F403

__all__ = [
    "TOML_LOADER",
    "TOML_RESULT",
    "InvalidTomlError",
    "load_toml_or_inline_map",
    "read_toml_content",
]
