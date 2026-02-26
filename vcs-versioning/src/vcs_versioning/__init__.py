"""VCS-based versioning for Python packages

Core functionality for version management based on VCS metadata.
"""

from __future__ import annotations

from typing import Any

# Public API exports
from ._config import DEFAULT_LOCAL_SCHEME, DEFAULT_VERSION_SCHEME, Configuration
from ._pyproject_reading import PyProjectData
from ._scm_version import ScmVersion
from ._version_cls import NonNormalizedVersion, Version
from ._version_inference import infer_version_string


def build_configuration_from_pyproject(
    pyproject_data: PyProjectData,
    *,
    dist_name: str | None = None,
    **integrator_overrides: Any,
) -> Configuration:
    """Build Configuration from PyProjectData with full workflow.

    EXPERIMENTAL API for integrators.

    This helper orchestrates the complete configuration building workflow:
    1. Extract config from pyproject_data.section
    2. Determine dist_name (argument > pyproject.project_name)
    3. Apply integrator overrides (override config file)
    4. Apply environment TOML overrides (highest priority)
    5. Create and validate Configuration instance

    Integrators create PyProjectData themselves:

    Example 1 - From file:
        >>> from vcs_versioning import PyProjectData, build_configuration_from_pyproject
        >>> from vcs_versioning.overrides import GlobalOverrides
        >>>
        >>> with GlobalOverrides.from_env("HATCH_VCS", dist_name="my-pkg"):
        ...     pyproject = PyProjectData.from_file("pyproject.toml")
        ...     config = build_configuration_from_pyproject(
        ...         pyproject_data=pyproject,
        ...         dist_name="my-pkg",
        ...     )

    Example 2 - Manual composition:
        >>> from pathlib import Path
        >>> from vcs_versioning import PyProjectData, build_configuration_from_pyproject
        >>>
        >>> pyproject = PyProjectData(
        ...     path=Path("pyproject.toml"),
        ...     tool_name="vcs-versioning",
        ...     project={"name": "my-pkg"},
        ...     section={"local_scheme": "no-local-version"},
        ...     is_required=True,
        ...     section_present=True,
        ...     project_present=True,
        ...     build_requires=[],
        ... )
        >>> config = build_configuration_from_pyproject(
        ...     pyproject_data=pyproject,
        ...     version_scheme="semver-pep440-release-branch",  # Integrator override
        ... )

    Args:
        pyproject_data: Parsed pyproject data (integrator creates this)
        dist_name: Distribution name (overrides pyproject_data.project_name)
        **integrator_overrides: Integrator-provided config overrides
                               (override config file, but overridden by env)

    Returns:
        Configured Configuration instance ready for version inference

    Priority order (highest to lowest):
        1. Environment TOML overrides (TOOL_OVERRIDES_FOR_DIST, TOOL_OVERRIDES)
        2. Integrator **overrides arguments
        3. pyproject_data.section configuration
        4. Configuration defaults

    This allows integrators to provide their own transformations
    while still respecting user environment variable overrides.
    """
    from ._integrator_helpers import build_configuration_from_pyproject_internal

    return build_configuration_from_pyproject_internal(
        pyproject_data=pyproject_data,
        dist_name=dist_name,
        **integrator_overrides,
    )


__all__ = [
    "DEFAULT_LOCAL_SCHEME",
    "DEFAULT_VERSION_SCHEME",
    "Configuration",
    "NonNormalizedVersion",
    "PyProjectData",
    "ScmVersion",
    "Version",
    "build_configuration_from_pyproject",
    "infer_version_string",
]

# Experimental API markers for documentation
__experimental__ = [
    "PyProjectData",
    "build_configuration_from_pyproject",
]
