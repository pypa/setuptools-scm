"""Internal implementation details for the overrides module.

This module contains private helpers and functions used internally
by vcs_versioning. Public API is exposed via the overrides module.
"""

from __future__ import annotations

import dataclasses
import logging
from collections.abc import Mapping
from difflib import get_close_matches
from typing import Any

from packaging.utils import canonicalize_name

from . import _config
from . import _version_schemes as version
from ._toml import load_toml_or_inline_map

log = logging.getLogger(__name__)

PRETEND_KEY = "SETUPTOOLS_SCM_PRETEND_VERSION"
PRETEND_KEY_NAMED = PRETEND_KEY + "_FOR_{name}"
PRETEND_METADATA_KEY = "SETUPTOOLS_SCM_PRETEND_METADATA"
PRETEND_METADATA_KEY_NAMED = PRETEND_METADATA_KEY + "_FOR_{name}"


def _search_env_vars_with_prefix(
    prefix: str, dist_name: str, env: Mapping[str, str]
) -> list[tuple[str, str]]:
    """Search environment variables with a given prefix for potential dist name matches.

    Args:
        prefix: The environment variable prefix (e.g., "SETUPTOOLS_SCM_PRETEND_VERSION_FOR_")
        dist_name: The original dist name to match against
        env: Environment dictionary to search in

    Returns:
        List of (env_var_name, env_var_value) tuples for potential matches
    """
    # Get the canonical name for comparison
    canonical_dist_name = canonicalize_name(dist_name)

    matches = []
    for env_var, value in env.items():
        if env_var.startswith(prefix):
            suffix = env_var[len(prefix) :]
            # Normalize the suffix and compare to canonical dist name
            try:
                normalized_suffix = canonicalize_name(suffix.lower().replace("_", "-"))
                if normalized_suffix == canonical_dist_name:
                    matches.append((env_var, value))
            except Exception:
                # If normalization fails for any reason, skip this env var
                continue

    return matches


def _find_close_env_var_matches(
    prefix: str, expected_suffix: str, env: Mapping[str, str], threshold: float = 0.6
) -> list[str]:
    """Find environment variables with similar suffixes that might be typos.

    Args:
        prefix: The environment variable prefix
        expected_suffix: The expected suffix (canonicalized dist name in env var format)
        env: Environment dictionary to search in
        threshold: Similarity threshold for matches (0.0 to 1.0)

    Returns:
        List of environment variable names that are close matches
    """
    candidates = []
    for env_var in env:
        if env_var.startswith(prefix):
            suffix = env_var[len(prefix) :]
            candidates.append(suffix)

    # Use difflib to find close matches
    close_matches_list = get_close_matches(
        expected_suffix, candidates, n=3, cutoff=threshold
    )

    return [
        f"{prefix}{match}" for match in close_matches_list if match != expected_suffix
    ]


def _read_pretended_metadata_for(
    config: _config.Configuration,
) -> dict[str, Any] | None:
    """read overridden metadata from the environment

    tries ``SETUPTOOLS_SCM_PRETEND_METADATA``
    and ``SETUPTOOLS_SCM_PRETEND_METADATA_FOR_$UPPERCASE_DIST_NAME``

    Returns a dictionary with metadata field overrides like:
    {"node": "g1337beef", "distance": 4}
    """
    import os

    from .overrides import EnvReader

    log.debug("dist name: %s", config.dist_name)

    reader = EnvReader(
        tools_names=("SETUPTOOLS_SCM", "VCS_VERSIONING"),
        env=os.environ,
        dist_name=config.dist_name,
    )
    pretended = reader.read("PRETEND_METADATA")

    if pretended:
        try:
            metadata_overrides = load_toml_or_inline_map(pretended)
            # Validate that only known ScmVersion fields are provided
            valid_fields = {
                "tag",
                "distance",
                "node",
                "dirty",
                "preformatted",
                "branch",
                "node_date",
                "time",
            }
            invalid_fields = set(metadata_overrides.keys()) - valid_fields
            if invalid_fields:
                log.warning(
                    "Invalid metadata fields in pretend metadata: %s. "
                    "Valid fields are: %s",
                    invalid_fields,
                    valid_fields,
                )
                # Remove invalid fields but continue processing
                for field in invalid_fields:
                    metadata_overrides.pop(field)

            return metadata_overrides or None
        except Exception as e:
            log.error("Failed to parse pretend metadata: %s", e)
            return None
    else:
        return None


def _apply_metadata_overrides(
    scm_version: version.ScmVersion | None,
    config: _config.Configuration,
) -> version.ScmVersion | None:
    """Apply metadata overrides to a ScmVersion object.

    This function reads pretend metadata from environment variables and applies
    the overrides to the given ScmVersion. TOML type coercion is used so values
    should be provided in their correct types (int, bool, datetime, etc.).

    Args:
        scm_version: The ScmVersion to apply overrides to, or None
        config: Configuration object

    Returns:
        Modified ScmVersion with overrides applied, or None
    """
    metadata_overrides = _read_pretended_metadata_for(config)

    if not metadata_overrides:
        return scm_version

    if scm_version is None:
        log.warning(
            "PRETEND_METADATA specified but no base version found. "
            "Metadata overrides cannot be applied without a base version."
        )
        return None

    log.info("Applying metadata overrides: %s", metadata_overrides)

    # Define type checks and field mappings
    from datetime import date, datetime

    field_specs: dict[str, tuple[type | tuple[type, type], str]] = {
        "distance": (int, "int"),
        "dirty": (bool, "bool"),
        "preformatted": (bool, "bool"),
        "node_date": (date, "date"),
        "time": (datetime, "datetime"),
        "node": ((str, type(None)), "str or None"),
        "branch": ((str, type(None)), "str or None"),
        # tag is special - can be multiple types, handled separately
    }

    # Apply each override individually using dataclasses.replace for type safety
    result = scm_version

    for field, value in metadata_overrides.items():
        if field in field_specs:
            expected_type, type_name = field_specs[field]
            assert isinstance(value, expected_type), (
                f"{field} must be {type_name}, got {type(value).__name__}: {value!r}"
            )
            result = dataclasses.replace(result, **{field: value})
        elif field == "tag":
            # tag can be Version, NonNormalizedVersion, or str - we'll let the assignment handle validation
            result = dataclasses.replace(result, tag=value)
        else:
            # This shouldn't happen due to validation in _read_pretended_metadata_for
            log.warning("Unknown field '%s' in metadata overrides", field)

    # Ensure config is preserved (should not be overridden)
    assert result.config is config, "Config must be preserved during metadata overrides"

    return result


def _read_pretended_version_for(
    config: _config.Configuration,
) -> version.ScmVersion | None:
    """read a a overridden version from the environment

    tries ``SETUPTOOLS_SCM_PRETEND_VERSION``
    and ``SETUPTOOLS_SCM_PRETEND_VERSION_FOR_$UPPERCASE_DIST_NAME``
    """
    import os

    from .overrides import EnvReader

    log.debug("dist name: %s", config.dist_name)

    reader = EnvReader(
        tools_names=("SETUPTOOLS_SCM", "VCS_VERSIONING"),
        env=os.environ,
        dist_name=config.dist_name,
    )
    pretended = reader.read("PRETEND_VERSION")

    if pretended:
        return version.meta(tag=pretended, preformatted=True, config=config)
    else:
        return None


def read_toml_overrides(dist_name: str | None) -> dict[str, Any]:
    """Read TOML overrides from environment."""
    import os

    from .overrides import EnvReader

    reader = EnvReader(
        tools_names=("SETUPTOOLS_SCM", "VCS_VERSIONING"),
        env=os.environ,
        dist_name=dist_name,
    )
    return reader.read_toml("OVERRIDES")
