# ruff: noqa: F405
"""Re-export _run_cmd from vcs_versioning for backward compatibility"""

from __future__ import annotations

from vcs_versioning._run_cmd import *  # noqa: F403

__all__ = [
    "CommandNotFoundError",
    "CompletedProcess",
    "require_command",
    "run",
]
