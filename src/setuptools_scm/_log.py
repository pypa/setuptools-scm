# ruff: noqa: F405
"""Re-export log from vcs_versioning for backward compatibility"""

from __future__ import annotations

from vcs_versioning._log import *  # noqa: F403

__all__ = ["log"]
