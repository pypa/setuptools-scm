#!/usr/bin/env python3
"""Extract version from CHANGELOG.md file.

This script extracts the most recent version number from a CHANGELOG.md file
by finding the first version heading.
"""

import re
import sys
from pathlib import Path


def extract_version_from_changelog(changelog_path: Path) -> str | None:
    """Extract the first version number from a changelog file.

    Args:
        changelog_path: Path to CHANGELOG.md

    Returns:
        Version string (e.g., "9.2.2") or None if not found
    """
    if not changelog_path.exists():
        return None

    content = changelog_path.read_text()

    # Look for version patterns like:
    # ## 9.2.2 (2024-01-15)
    # ## v9.2.2
    # ## [9.2.2]
    version_pattern = r"^##\s+(?:\[)?v?(\d+\.\d+\.\d+(?:\.\d+)?)"

    for line in content.splitlines():
        match = re.match(version_pattern, line)
        if match:
            return match.group(1)

    return None


def main() -> None:
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: extract_version.py <path-to-changelog>", file=sys.stderr)
        sys.exit(1)

    changelog_path = Path(sys.argv[1])
    version = extract_version_from_changelog(changelog_path)

    if version:
        print(version)
    else:
        print("No version found in changelog", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
