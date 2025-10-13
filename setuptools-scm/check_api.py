#!/usr/bin/env python3
"""
Local script to check API stability using griffe.

Usage:
    uv run check_api.py [--against TAG]

This script runs griffe with the public-wildcard-imports extension enabled
to properly detect re-exported symbols from vcs-versioning.
"""

from __future__ import annotations

import subprocess
import sys

from pathlib import Path


def main() -> int:
    """Run griffe API check with proper configuration."""
    # Parse arguments
    against = "v9.2.1"  # Default baseline
    if len(sys.argv) > 1:
        if sys.argv[1] == "--against" and len(sys.argv) > 2:
            against = sys.argv[2]
        else:
            against = sys.argv[1]

    # Ensure we're in the right directory
    repo_root = Path(__file__).parent.parent

    # Build griffe command
    cmd = [
        "griffe",
        "check",
        "setuptools_scm",
        "-ssetuptools-scm/src",
        "-svcs-versioning/src",
        "--verbose",
        *("--extensions", "griffe_public_wildcard_imports"),
        "--against",
        against,
    ]

    result = subprocess.run(cmd, cwd=repo_root)

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
