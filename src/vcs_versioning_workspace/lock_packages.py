#!/usr/bin/env python3
"""Generate per-package uv.lock files for sdist shipping.

uv workspaces use a single lock file for the entire workspace.
This tool temporarily hides the workspace root so each member
package can resolve its dependencies independently.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MEMBERS = ["vcs-versioning", "setuptools-scm"]


def lock_packages(root: Path) -> None:
    """Generate per-package uv.lock files by hiding the workspace root."""
    workspace_pyproject = root / "pyproject.toml"
    workspace_lock = root / "uv.lock"

    if not workspace_pyproject.exists():
        print("error: pyproject.toml not found at workspace root", file=sys.stderr)
        sys.exit(1)

    try:
        workspace_pyproject.unlink()
        workspace_lock.unlink(missing_ok=True)

        for member in MEMBERS:
            member_dir = root / member
            if not (member_dir / "pyproject.toml").exists():
                print(f"warning: {member}/pyproject.toml not found, skipping")
                continue
            print(f"locking {member}...")
            subprocess.check_call(["uv", "lock"], cwd=member_dir)

    finally:
        subprocess.check_call(
            ["git", "checkout", "pyproject.toml", "uv.lock"], cwd=root
        )


def main() -> None:
    root = Path.cwd()
    lock_packages(root)
    print("done: per-package uv.lock files generated")


if __name__ == "__main__":
    main()
