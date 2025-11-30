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

from .._scm_version import ScmVersion
from ._common import SEMVER_MINOR, SEMVER_PATCH
from ._standard import guess_next_dev_version, guess_next_simple_semver

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


def _get_changelog_root(version: ScmVersion) -> Path:
    """Get the root directory where changelog.d/ should be located.

    For monorepo support, prefers relative_to (config file location).
    Falls back to absolute_root (VCS root).
    """
    import os

    if version.config.relative_to:
        # relative_to is typically the pyproject.toml file path
        # changelog.d/ should be in the same directory
        if os.path.isfile(version.config.relative_to):
            return Path(os.path.dirname(version.config.relative_to))
        else:
            return Path(version.config.relative_to)
    else:
        # When no relative_to is set, use absolute_root (the VCS root)
        return Path(version.config.absolute_root)


def _guess_next_major(version: ScmVersion) -> str:
    """Guess next major version (X+1.0.0) from current tag."""
    from .. import _modify_version

    tag_version = _modify_version.strip_local(str(version.tag))
    parts = tag_version.split(".")
    if len(parts) >= 1:
        major = int(parts[0].lstrip("v"))  # Handle 'v' prefix
        return f"{major + 1}.0.0"
    # Fallback to bump_dev
    bumped = _modify_version._bump_dev(tag_version)
    return bumped if bumped is not None else f"{tag_version}.dev0"


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

    root = _get_changelog_root(version)
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
        return version.format_next_version(_guess_next_major)

    elif bump_type == "minor":
        return version.format_next_version(
            guess_next_simple_semver, retain=SEMVER_MINOR
        )

    else:  # patch
        return version.format_next_version(
            guess_next_simple_semver, retain=SEMVER_PATCH
        )


def get_release_version(version: ScmVersion) -> str | None:
    """Get clean release version from towncrier fragments (no .devN suffix).

    Unlike version_from_fragments(), this returns only the clean version
    string (e.g., "10.0.0") without .devN suffix. Used by release tooling.

    Args:
        version: ScmVersion object from VCS

    Returns:
        Clean version string, or None if no fragments found
    """
    # If we're exactly on a tag, return it
    if version.exact:
        return version.format_with("{tag}")

    root = _get_changelog_root(version)
    log.debug("Analyzing fragments for release version in %s", root)

    fragments = _find_fragments(root)
    bump_type = _determine_bump_type(fragments)

    if bump_type is None:
        log.debug("No fragments found, cannot determine release version")
        return None

    log.info("Determined release version bump type from fragments: %s", bump_type)

    # KEY DIFFERENCE: Use fmt="{guessed}" for clean version (no .devN)
    if bump_type == "major":
        return version.format_next_version(_guess_next_major, fmt="{guessed}")

    elif bump_type == "minor":
        return version.format_next_version(
            guess_next_simple_semver, fmt="{guessed}", retain=SEMVER_MINOR
        )

    else:  # patch
        return version.format_next_version(
            guess_next_simple_semver, fmt="{guessed}", retain=SEMVER_PATCH
        )
