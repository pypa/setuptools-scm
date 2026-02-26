"""Internal helpers for integrators to build configurations.

This module provides substantial orchestration functions for building
Configuration instances with proper override priority handling.

Public API is exposed through __init__.py with restrictions.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ._config import Configuration
    from ._pyproject_reading import PyProjectData

log = logging.getLogger(__name__)


def build_configuration_from_pyproject_internal(
    pyproject_data: PyProjectData,
    *,
    dist_name: str | None = None,
    **integrator_overrides: Any,
) -> Configuration:
    """Build Configuration with complete workflow orchestration.

    This is a substantial helper that orchestrates the complete configuration
    building workflow with proper priority handling.

    Orchestration steps:
    1. Extract base config from pyproject_data.section
    2. Determine dist_name (argument > pyproject.project_name)
    3. Merge integrator overrides (override config file)
    4. Read and apply env TOML overrides (highest priority)
    5. Build Configuration with proper validation

    Priority order (highest to lowest):
        1. Environment TOML overrides (TOOL_OVERRIDES_FOR_DIST, TOOL_OVERRIDES)
        2. Integrator **integrator_overrides arguments
        3. pyproject_data.section configuration
        4. Configuration defaults

    Args:
        pyproject_data: Parsed pyproject data from PyProjectData.from_file() or manual composition
        dist_name: Distribution name for env var lookups (overrides pyproject_data.project_name)
        **integrator_overrides: Integrator-provided config overrides
                               (override config file, but overridden by env)

    Returns:
        Configured Configuration instance ready for version inference

    Example:
        >>> from vcs_versioning import PyProjectData
        >>> from vcs_versioning._integrator_helpers import build_configuration_from_pyproject_internal
        >>>
        >>> pyproject = PyProjectData.from_file(
        ...     "pyproject.toml",
        ...     _tool_names=["setuptools_scm", "vcs-versioning"]
        ... )
        >>> config = build_configuration_from_pyproject_internal(
        ...     pyproject_data=pyproject,
        ...     dist_name="my-package",
        ...     local_scheme="no-local-version",  # Integrator override
        ... )
    """
    # Import here to avoid circular dependencies
    from ._config import Configuration
    from ._overrides import read_toml_overrides
    from ._pyproject_reading import get_args_for_pyproject

    # Step 1: Get base config from pyproject section
    # This also handles dist_name resolution
    log.debug(
        "Building configuration from pyproject at %s (tool: %s)",
        pyproject_data.path,
        pyproject_data.tool_name,
    )

    config_data = get_args_for_pyproject(
        pyproject_data,
        dist_name=dist_name,
        kwargs={},
    )

    # Step 2: dist_name is now determined (from arg, config, or project.name)
    actual_dist_name = config_data.get("dist_name")
    log.debug("Resolved dist_name: %s", actual_dist_name)

    # Step 3: Merge integrator overrides (middle priority - override config file)
    if integrator_overrides:
        log.debug(
            "Applying integrator overrides: %s", list(integrator_overrides.keys())
        )
        config_data.update(integrator_overrides)

    # Step 4: Apply environment TOML overrides (highest priority)
    env_overrides = read_toml_overrides(actual_dist_name)
    if env_overrides:
        log.debug("Applying environment TOML overrides: %s", list(env_overrides.keys()))
        config_data.update(env_overrides)

    # Step 5: Build Configuration with validation
    relative_to = pyproject_data.path
    log.debug("Building Configuration with relative_to=%s", relative_to)

    return Configuration.from_data(relative_to=relative_to, data=config_data)


__all__ = [
    "build_configuration_from_pyproject_internal",
]
