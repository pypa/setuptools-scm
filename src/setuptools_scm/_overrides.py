from __future__ import annotations

import dataclasses
import os
import re

from typing import Any

from . import _config
from . import _log
from . import version
from ._integration.toml import load_toml_or_inline_map

log = _log.log.getChild("overrides")

PRETEND_KEY = "SETUPTOOLS_SCM_PRETEND_VERSION"
PRETEND_KEY_NAMED = PRETEND_KEY + "_FOR_{name}"
PRETEND_METADATA_KEY = "SETUPTOOLS_SCM_PRETEND_METADATA"
PRETEND_METADATA_KEY_NAMED = PRETEND_METADATA_KEY + "_FOR_{name}"


def read_named_env(
    *, tool: str = "SETUPTOOLS_SCM", name: str, dist_name: str | None
) -> str | None:
    """ """
    if dist_name is not None:
        # Normalize the dist name as per PEP 503.
        normalized_dist_name = re.sub(r"[-_.]+", "-", dist_name)
        env_var_dist_name = normalized_dist_name.replace("-", "_").upper()
        val = os.environ.get(f"{tool}_{name}_FOR_{env_var_dist_name}")
        if val is not None:
            return val
    return os.environ.get(f"{tool}_{name}")


def _read_pretended_metadata_for(
    config: _config.Configuration,
) -> dict[str, Any] | None:
    """read overridden metadata from the environment

    tries ``SETUPTOOLS_SCM_PRETEND_METADATA``
    and ``SETUPTOOLS_SCM_PRETEND_METADATA_FOR_$UPPERCASE_DIST_NAME``

    Returns a dictionary with metadata field overrides like:
    {"node": "g1337beef", "distance": 4}
    """
    log.debug("dist name: %s", config.dist_name)

    pretended = read_named_env(name="PRETEND_METADATA", dist_name=config.dist_name)

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
    from datetime import date
    from datetime import datetime

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
    log.debug("dist name: %s", config.dist_name)

    pretended = read_named_env(name="PRETEND_VERSION", dist_name=config.dist_name)

    if pretended:
        # Use enhanced meta function - let validation errors bubble up
        return version.meta(tag=pretended, preformatted=True, config=config)
    else:
        return None


def read_toml_overrides(dist_name: str | None) -> dict[str, Any]:
    data = read_named_env(name="OVERRIDES", dist_name=dist_name)
    return load_toml_or_inline_map(data)
