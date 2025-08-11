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
            missing_file_ok=True,
            missing_section_ok=True,
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
    if dist_name is None:
        dist_name = pyproject_data.project_name

    # Handle version already set
    if current_version is not None:
        if was_set_by_infer:
            if overrides is not None and overrides:
                # Clear version and proceed with actual overrides (non-empty dict)
                return VersionInferenceConfig(
                    dist_name=dist_name,
                    pyproject_data=pyproject_data,
                    overrides=overrides,
                )
            else:
                # Keep existing version from infer_version (no overrides or empty overrides)
                # But allow re-inferring if this is another infer_version call
                if overrides is None:
                    # This is another infer_version call, allow it to proceed
                    return VersionInferenceConfig(
                        dist_name=dist_name,
                        pyproject_data=pyproject_data,
                        overrides=overrides,
                    )
                else:
                    # This is version_keyword with empty overrides, keep existing version
                    return VersionInferenceNoOp()
        else:
            # Version set by something else
            return VersionInferenceError(
                f"version of {dist_name} already set", should_warn=True
            )

    # Handle setuptools-scm package
    if dist_name == "setuptools-scm":
        return VersionInferenceNoOp()

    # Handle missing configuration
    if not pyproject_data.is_required and not pyproject_data.section_present:
        # If version_keyword was called (overrides is not None), activate setuptools_scm
        # This handles both use_scm_version=True (empty {}) and use_scm_version={config}
        if overrides is not None:
            return VersionInferenceConfig(
                dist_name=dist_name,
                pyproject_data=pyproject_data,
                overrides=overrides,
            )
        # If infer_version was called (overrides is None), only activate with config
        return VersionInferenceNoOp()

    # Handle missing project section when required
    if (
        pyproject_data.is_required
        and not pyproject_data.section_present
        and not pyproject_data.project_present
        and overrides is None  # Only return NoOp for infer_version, not version_keyword
    ):
        return VersionInferenceNoOp()

    # All conditions met - proceed with inference
    return VersionInferenceConfig(
        dist_name=dist_name,
        pyproject_data=pyproject_data,
        overrides=overrides,
    )
