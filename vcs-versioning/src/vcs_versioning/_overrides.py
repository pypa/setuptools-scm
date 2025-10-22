"""Internal implementation details for the overrides module.

This module contains private helpers and functions used internally
by vcs_versioning. Public API is exposed via the overrides module.
"""

from __future__ import annotations

import dataclasses
import logging
import os
from collections.abc import Mapping
from datetime import date, datetime
from difflib import get_close_matches
from re import Pattern
from typing import Any, TypedDict, get_type_hints

from packaging.utils import canonicalize_name

from . import _config
from . import _types as _t
from . import _version_schemes as version
from ._version_cls import Version as _Version

log = logging.getLogger(__name__)


# TypedDict schemas for TOML data validation and type hints


class PretendMetadataDict(TypedDict, total=False):
    """Schema for ScmVersion metadata fields that can be overridden via environment.

    All fields are optional since partial overrides are allowed.
    """

    tag: str | _Version
    distance: int
    node: str | None
    dirty: bool
    preformatted: bool
    branch: str | None
    node_date: date | None
    time: datetime


class ConfigOverridesDict(TypedDict, total=False):
    """Schema for Configuration fields that can be overridden via environment.

    All fields are optional since partial overrides are allowed.
    """

    # Configuration fields
    root: _t.PathT
    version_scheme: _t.VERSION_SCHEME
    local_scheme: _t.VERSION_SCHEME
    tag_regex: str | Pattern[str]
    parentdir_prefix_version: str | None
    fallback_version: str | None
    fallback_root: _t.PathT
    write_to: _t.PathT | None
    write_to_template: str | None
    version_file: _t.PathT | None
    version_file_template: str | None
    parse: Any  # ParseFunction - avoid circular import
    git_describe_command: _t.CMD_TYPE | None  # deprecated but still supported
    dist_name: str | None
    version_cls: Any  # type[_Version] - avoid circular import
    normalize: bool  # Used in from_data
    search_parent_directories: bool
    parent: _t.PathT | None
    scm: dict[str, Any]  # Nested SCM configuration


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
) -> PretendMetadataDict | None:
    """read overridden metadata from the environment

    tries ``SETUPTOOLS_SCM_PRETEND_METADATA``
    and ``SETUPTOOLS_SCM_PRETEND_METADATA_FOR_$UPPERCASE_DIST_NAME``

    Returns a dictionary with metadata field overrides like:
    {"node": "g1337beef", "distance": 4}
    """
    from .overrides import EnvReader

    log.debug("dist name: %s", config.dist_name)

    reader = EnvReader(
        tools_names=("SETUPTOOLS_SCM", "VCS_VERSIONING"),
        env=os.environ,
        dist_name=config.dist_name,
    )

    try:
        # Use schema validation during TOML parsing
        metadata_overrides = reader.read_toml(
            "PRETEND_METADATA", schema=PretendMetadataDict
        )
        return metadata_overrides or None
    except Exception as e:
        log.error("Failed to parse pretend metadata: %s", e)
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

    # Get type hints from PretendMetadataDict for validation
    field_types = get_type_hints(PretendMetadataDict)

    # Apply each override individually using dataclasses.replace
    result = scm_version

    for field, value in metadata_overrides.items():
        # Validate field types using the TypedDict annotations
        if field in field_types:
            expected_type = field_types[field]
            # Handle Optional/Union types (e.g., str | None)
            if hasattr(expected_type, "__args__"):
                # Union type - check if value is instance of any of the types
                valid = any(
                    isinstance(value, t) if t is not type(None) else value is None
                    for t in expected_type.__args__
                )
                if not valid:
                    type_names = " | ".join(
                        t.__name__ if t is not type(None) else "None"
                        for t in expected_type.__args__
                    )
                    raise TypeError(
                        f"Field '{field}' must be {type_names}, "
                        f"got {type(value).__name__}: {value!r}"
                    )
            else:
                # Simple type
                if not isinstance(value, expected_type):
                    raise TypeError(
                        f"Field '{field}' must be {expected_type.__name__}, "
                        f"got {type(value).__name__}: {value!r}"
                    )

        result = dataclasses.replace(result, **{field: value})  # type: ignore[arg-type]

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


def read_toml_overrides(dist_name: str | None) -> ConfigOverridesDict:
    """Read TOML overrides from environment.

    Validates that only known Configuration fields are provided.
    """
    from .overrides import EnvReader

    reader = EnvReader(
        tools_names=("SETUPTOOLS_SCM", "VCS_VERSIONING"),
        env=os.environ,
        dist_name=dist_name,
    )
    return reader.read_toml("OVERRIDES", schema=ConfigOverridesDict)
