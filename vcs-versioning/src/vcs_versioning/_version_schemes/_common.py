"""Common utilities shared across version schemes."""

from __future__ import annotations

# Semantic versioning constants
SEMVER_MINOR = 2
SEMVER_PATCH = 3
SEMVER_LEN = 3


def combine_version_with_local_parts(
    main_version: str, *local_parts: str | None
) -> str:
    """
    Combine a main version with multiple local parts into a valid PEP 440 version string.
    Handles deduplication of local parts to avoid adding the same local data twice.

    Args:
        main_version: The main version string (e.g., "1.2.0", "1.2.dev3")
        *local_parts: Variable number of local version parts, can be None or empty

    Returns:
        A valid PEP 440 version string

    Examples:
        combine_version_with_local_parts("1.2.0", "build.123", "d20090213") -> "1.2.0+build.123.d20090213"
        combine_version_with_local_parts("1.2.0", "build.123", None) -> "1.2.0+build.123"
        combine_version_with_local_parts("1.2.0+build.123", "d20090213") -> "1.2.0+build.123.d20090213"
        combine_version_with_local_parts("1.2.0+build.123", "build.123") -> "1.2.0+build.123"  # no duplication
        combine_version_with_local_parts("1.2.0", None, None) -> "1.2.0"
    """
    # Split main version into base and existing local parts
    if "+" in main_version:
        main_part, existing_local = main_version.split("+", 1)
        all_local_parts = existing_local.split(".")
    else:
        main_part = main_version
        all_local_parts = []

    # Process each new local part
    for part in local_parts:
        if not part or not part.strip():
            continue

        # Strip any leading + and split into segments
        clean_part = part.strip("+")
        if not clean_part:
            continue

        # Split multi-part local identifiers (e.g., "build.123" -> ["build", "123"])
        part_segments = clean_part.split(".")

        # Add each segment if not already present
        for segment in part_segments:
            if segment and segment not in all_local_parts:
                all_local_parts.append(segment)

    # Return combined result
    if all_local_parts:
        return main_part + "+" + ".".join(all_local_parts)
    else:
        return main_part
