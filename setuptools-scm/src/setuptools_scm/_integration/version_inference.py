from __future__ import annotations

import logging
import os

from dataclasses import dataclass
from typing import Any
from typing import Protocol
from typing import TypeAlias

from setuptools import Distribution
from vcs_versioning._pyproject_reading import PyProjectData

from .build_py import VersionInferenceData
from .build_py import set_version_inference_data
from .pyproject_reading import should_infer

log = logging.getLogger(__name__)

# Environment variable to force writing version files at inference time
# instead of deferring to build_py. Useful for development workflows.
WRITE_TO_SOURCE_ENV_VAR = "SETUPTOOLS_SCM_WRITE_TO_SOURCE"


def _should_write_to_source() -> bool:
    """Check if version files should be written to source at inference time.

    Returns True if SETUPTOOLS_SCM_WRITE_TO_SOURCE env var is set to a truthy value.
    """
    value = os.environ.get(WRITE_TO_SOURCE_ENV_VAR, "").lower()
    return value in ("1", "true", "yes")


def infer_version_with_config(
    dist_name: str | None,
    pyproject_data: PyProjectData,
    overrides: dict[str, Any] | None = None,
) -> VersionInferenceData:
    """Infer version and return VersionInferenceData.

    By default, version files are NOT written to the source tree during inference.
    Instead, they are written to the build directory during build_py.

    Set SETUPTOOLS_SCM_WRITE_TO_SOURCE=1 to force writing version files to the
    source tree at inference time (useful for development workflows).

    Returns:
        VersionInferenceData containing version string, Configuration, and ScmVersion
    """
    from vcs_versioning._config import Configuration
    from vcs_versioning._get_version_impl import _version_missing
    from vcs_versioning._get_version_impl import parse_version
    from vcs_versioning._get_version_impl import write_version_files
    from vcs_versioning._version_schemes import format_version

    config = Configuration.from_file(
        dist_name=dist_name, pyproject_data=pyproject_data, **(overrides or {})
    )

    # Parse once to get the ScmVersion object
    scm_version = parse_version(config)
    if scm_version is None:
        _version_missing(config)

    # Format version string from the parsed ScmVersion
    version_string = format_version(scm_version)

    # Only write to source tree if explicitly requested via env var
    if _should_write_to_source():
        write_version_files(config, version=version_string, scm_version=scm_version)

    return VersionInferenceData(
        version=version_string,
        config=config,
        scm_version=scm_version,
    )


class VersionInferenceApplicable(Protocol):
    """A result object from version inference decision that can be applied to a dist."""

    def apply(self, dist: Distribution) -> None:  # pragma: no cover - structural type
        ...


class GetVersionInferenceConfig(Protocol):
    """Callable protocol for the decision function used by integration points."""

    def __call__(
        self,
        dist_name: str | None,
        current_version: str | None,
        pyproject_data: PyProjectData,
        overrides: dict[str, object] | None = None,
    ) -> VersionInferenceApplicable:  # pragma: no cover - structural type
        ...


@dataclass
class VersionInferenceConfig:
    """Configuration for version inference."""

    dist_name: str | None
    pyproject_data: PyProjectData | None
    overrides: dict[str, Any] | None

    def apply(self, dist: Distribution) -> None:
        """Apply version inference to the distribution.

        Version files are NOT written to the source tree. Instead, the version
        inference data (Configuration and ScmVersion) is stored on the distribution
        for the build_py command to write to the build directory. This supports
        read-only source installations (e.g., Bazel builds).
        """
        data = infer_version_with_config(
            self.dist_name,
            self.pyproject_data,  # type: ignore[arg-type]
            self.overrides,
        )
        dist.metadata.version = data.version

        # Store version inference data for build_py to write to build directory
        set_version_inference_data(dist, data)
        log.debug(
            "Stored version inference data for build_py: version=%s", data.version
        )

        # Mark that this version was set by infer_version if overrides is None (infer_version context)
        if self.overrides is None:
            dist._setuptools_scm_version_set_by_infer = True  # type: ignore[attr-defined]


@dataclass
class VersionAlreadySetWarning:
    """Warning that version was already set, inference would override it."""

    dist_name: str | None

    def apply(self, dist: Distribution) -> None:
        """Warn user that version is already set."""
        import warnings

        warnings.warn(f"version of {self.dist_name} already set")


@dataclass(frozen=True)
class VersionInferenceNoOp:
    """No operation result - silent skip."""

    def apply(self, dist: Distribution) -> None:
        """Apply no-op to the distribution."""


VersionInferenceResult: TypeAlias = (
    VersionInferenceConfig  # Proceed with inference
    | VersionAlreadySetWarning  # Warn: version already set
    | VersionInferenceNoOp  # Don't infer (silent)
)


def infer_version_string(
    dist_name: str | None,
    pyproject_data: PyProjectData,
    overrides: dict[str, Any] | None = None,
    *,
    force_write_version_files: bool = False,
) -> str:
    """
    Compute the inferred version string from the given inputs without requiring a
    setuptools Distribution instance. This is a pure helper that simplifies
    integration tests by avoiding file I/O and side effects on a Distribution.

    Parameters:
        dist_name: Optional distribution name (used for overrides and env scoping)
        pyproject_data: Parsed PyProjectData (may be constructed via for_testing())
        overrides: Optional override configuration (same keys as [tool.setuptools_scm])
        force_write_version_files: When True, apply write_to/version_file effects

    Returns:
        The computed version string.
    """
    from vcs_versioning._version_inference import (
        infer_version_string as _vcs_infer_version_string,
    )

    # Delegate to vcs_versioning implementation
    return _vcs_infer_version_string(
        dist_name,
        pyproject_data,
        overrides,
        force_write_version_files=force_write_version_files,
    )


def get_version_inference_config(
    dist_name: str | None,
    current_version: str | None,
    pyproject_data: PyProjectData,
    overrides: dict[str, Any] | None = None,
) -> VersionInferenceResult:
    """
    Determine whether and how to perform version inference.

    Args:
        dist_name: The distribution name
        current_version: Current version if any
        pyproject_data: PyProjectData from parser (None if file doesn't exist)
        overrides: Override configuration (None for no overrides)

    Returns:
        VersionInferenceResult with the decision and configuration
    """

    config = VersionInferenceConfig(
        dist_name=dist_name,
        pyproject_data=pyproject_data,
        overrides=overrides,
    )

    inference_implied = should_infer(pyproject_data) or overrides is not None

    if inference_implied:
        if current_version is None:
            return config
        else:
            return VersionAlreadySetWarning(dist_name)
    else:
        return VersionInferenceNoOp()
