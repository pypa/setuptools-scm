from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any
from typing import Union

from .. import _log

if TYPE_CHECKING:
    from .pyproject_reading import PyProjectData

log = _log.log.getChild("version_inference")


@dataclass
class VersionInferenceConfig:
    """Configuration for version inference."""

    dist_name: str | None
    pyproject_data: PyProjectData | None
    overrides: dict[str, Any] | None

    def apply(self, dist: Any) -> None:
        """Apply version inference to the distribution."""
        from .. import _config as _config_module
        from .._get_version_impl import _get_version
        from .._get_version_impl import _version_missing

        # Clear version if it was set by infer_version (overrides is None means infer_version context)
        # OR if we have overrides (version_keyword context) and the version was set by infer_version
        was_set_by_infer = getattr(dist, "_setuptools_scm_version_set_by_infer", False)
        if was_set_by_infer and (self.overrides is None or self.overrides):
            dist._setuptools_scm_version_set_by_infer = False
            dist.metadata.version = None

        config = _config_module.Configuration.from_file(
            dist_name=self.dist_name,
            pyproject_data=self.pyproject_data,
            **(self.overrides or {}),
        )

        # Get and assign version
        maybe_version = _get_version(config, force_write_version_files=True)
        if maybe_version is None:
            _version_missing(config)
        else:
            assert dist.metadata.version is None
            dist.metadata.version = maybe_version

        # Mark that this version was set by infer_version if overrides is None (infer_version context)
        if self.overrides is None:
            dist._setuptools_scm_version_set_by_infer = True


@dataclass
class VersionInferenceError:
    """Error message for user."""

    message: str
    should_warn: bool = False

    def apply(self, dist: Any) -> None:
        """Apply error handling to the distribution."""
        import warnings

        if self.should_warn:
            warnings.warn(self.message)


@dataclass
class VersionInferenceException:
    """Exception that should be raised."""

    exception: Exception

    def apply(self, dist: Any) -> None:
        """Apply exception handling to the distribution."""
        raise self.exception


class VersionInferenceNoOp:
    """No operation result - silent skip."""

    def apply(self, dist: Any) -> None:
        """Apply no-op to the distribution."""


VersionInferenceResult = Union[
    VersionInferenceConfig,  # Proceed with inference
    VersionInferenceError,  # Show error/warning
    VersionInferenceException,  # Raise exception
    VersionInferenceNoOp,  # Don't infer (silent)
]


def get_version_inference_config(
    dist_name: str | None,
    current_version: str | None,
    pyproject_data: PyProjectData,
    overrides: dict[str, Any] | None = None,
    was_set_by_infer: bool = False,
) -> VersionInferenceResult:
    """
    Determine whether and how to perform version inference.

    Args:
        dist_name: The distribution name
        current_version: Current version if any
        pyproject_data: PyProjectData from parser (None if file doesn't exist)
        overrides: Override configuration (None for no overrides)
        was_set_by_infer: Whether current version was set by infer_version

    Returns:
        VersionInferenceResult with the decision and configuration
    """
    # Normalize name from project metadata when not provided
    if dist_name is None:
        dist_name = pyproject_data.project_name

    # If a version is already present, decide based on context (infer_version vs version_keyword)
    if current_version is not None:
        # infer_version call (overrides is None) should be a no-op if version already exists
        if overrides is None:
            return VersionInferenceNoOp()

        if not was_set_by_infer:
            return VersionInferenceError(
                f"version of {dist_name} already set",
                should_warn=pyproject_data.should_infer(),
            )

        # Version was set by infer_version previously
        if overrides:
            # Non-empty overrides from version_keyword → re-infer with overrides
            return VersionInferenceConfig(
                dist_name=dist_name, pyproject_data=pyproject_data, overrides=overrides
            )
        # Empty overrides dict from version_keyword → keep existing version
        return VersionInferenceNoOp()

    # Do not infer a version for setuptools-scm itself
    if dist_name == "setuptools-scm":
        return VersionInferenceNoOp()

    # version_keyword path: any overrides (empty or not) mean we should infer
    if overrides is not None:
        return VersionInferenceConfig(
            dist_name=dist_name, pyproject_data=pyproject_data, overrides=overrides
        )

    # infer_version path: only infer when [tool.setuptools_scm] section is present
    if pyproject_data.should_infer():
        return VersionInferenceConfig(
            dist_name=dist_name, pyproject_data=pyproject_data, overrides=None
        )

    return VersionInferenceNoOp()
