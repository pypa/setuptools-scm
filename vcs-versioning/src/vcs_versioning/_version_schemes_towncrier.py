"""Version scheme based on towncrier changelog fragments.

This version scheme analyzes changelog fragments in the changelog.d/ directory
to determine the appropriate version bump:
- Major bump: if 'removal' fragments are present
- Minor bump: if 'feature' or 'deprecation' fragments are present
- Patch bump: if only 'bugfix', 'doc', or 'misc' fragments are present

Falls back to guess-next-dev if no fragments are found.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ._version_schemes import (
    ScmVersion,
    guess_next_dev_version,
    guess_next_simple_semver,
)

log = logging.getLogger(__name__)

# Fragment types that indicate different version bumps
MAJOR_FRAGMENT_TYPES = {"removal"}
MINOR_FRAGMENT_TYPES = {"feature", "deprecation"}
PATCH_FRAGMENT_TYPES = {"bugfix", "doc", "misc"}

ALL_FRAGMENT_TYPES = MAJOR_FRAGMENT_TYPES | MINOR_FRAGMENT_TYPES | PATCH_FRAGMENT_TYPES


def _find_fragments(
    root: Path, changelog_dir: str = "changelog.d"
) -> dict[str, list[str]]:
    """Find and categorize changelog fragments.

    Args:
        root: Root directory to search from
        changelog_dir: Name of the changelog directory

    Returns:
        Dictionary mapping fragment types to lists of fragment filenames
    """
    fragments: dict[str, list[str]] = {ftype: [] for ftype in ALL_FRAGMENT_TYPES}

    changelog_path = root / changelog_dir
    if not changelog_path.exists():
        log.debug("No changelog directory found at %s", changelog_path)
        return fragments

    for entry in changelog_path.iterdir():
        if not entry.is_file():
            continue

        # Skip template, README, and .gitkeep files
        if entry.name in ("template.md", "README.md", ".gitkeep"):
            continue

        # Fragment naming: {number}.{type}.md
        parts = entry.name.split(".")
        if len(parts) >= 2:
            fragment_type = parts[1]
            if fragment_type in ALL_FRAGMENT_TYPES:
                fragments[fragment_type].append(entry.name)
                log.debug("Found %s fragment: %s", fragment_type, entry.name)

    return fragments


def _determine_bump_type(fragments: dict[str, list[str]]) -> str | None:
    """Determine version bump type from fragments.

    Returns:
        'major', 'minor', 'patch', or None if no fragments found
    """
    # Check for any fragments at all
    total_fragments = sum(len(files) for files in fragments.values())
    if total_fragments == 0:
        return None

    # Major bump if any removal fragments
    if any(fragments[ftype] for ftype in MAJOR_FRAGMENT_TYPES):
        return "major"

    # Minor bump if any feature/deprecation fragments
    if any(fragments[ftype] for ftype in MINOR_FRAGMENT_TYPES):
        return "minor"

    # Patch bump for other fragments
    if any(fragments[ftype] for ftype in PATCH_FRAGMENT_TYPES):
        return "patch"

    return None


def version_from_fragments(version: ScmVersion) -> str:
    """Version scheme that determines version from towncrier fragments.

    This is the main entry point registered as a setuptools_scm version scheme.

    Args:
        version: ScmVersion object from VCS

    Returns:
        Formatted version string
    """
    # If we're exactly on a tag, return it
    if version.exact:
        return version.format_with("{tag}")

    # Find where to look for changelog.d/ directory
    # Prefer relative_to (location of config file) for monorepo support
    # This allows changelog.d/ to be in the project dir rather than repo root
    if version.config.relative_to:
        # relative_to is typically the pyproject.toml file path
        # changelog.d/ should be in the same directory
        import os

        if os.path.isfile(version.config.relative_to):
            root = Path(os.path.dirname(version.config.relative_to))
        else:
            root = Path(version.config.relative_to)
    else:
        # When no relative_to is set, use absolute_root (the VCS root)
        root = Path(version.config.absolute_root)

    log.debug("Analyzing fragments in %s", root)

    # Find and analyze fragments
    fragments = _find_fragments(root)
    bump_type = _determine_bump_type(fragments)

    if bump_type is None:
        log.debug("No fragments found, falling back to guess-next-dev")
        return guess_next_dev_version(version)

    log.info("Determined version bump type from fragments: %s", bump_type)

    # Determine the next version based on bump type
    if bump_type == "major":
        # Major bump: increment major version, reset minor and patch to 0
        from . import _modify_version

        def guess_next_major(v: ScmVersion) -> str:
            tag_version = _modify_version.strip_local(str(v.tag))
            parts = tag_version.split(".")
            if len(parts) >= 1:
                major = int(parts[0].lstrip("v"))  # Handle 'v' prefix
                return f"{major + 1}.0.0"
            # Fallback to bump_dev
            bumped = _modify_version._bump_dev(tag_version)
            return bumped if bumped is not None else f"{tag_version}.dev0"

        return version.format_next_version(guess_next_major)

    elif bump_type == "minor":
        # Minor bump: use simplified semver with MINOR retention
        from ._version_schemes import SEMVER_MINOR

        return version.format_next_version(
            guess_next_simple_semver, retain=SEMVER_MINOR
        )

    else:  # patch
        # Patch bump: use simplified semver with PATCH retention
        from ._version_schemes import SEMVER_PATCH

        return version.format_next_version(
            guess_next_simple_semver, retain=SEMVER_PATCH
        )
