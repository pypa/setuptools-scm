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
    overrides: dict[str, Any]


@dataclass
class VersionInferenceError:
    """Error message for user."""

    message: str
    should_warn: bool = False


@dataclass
class VersionInferenceException:
    """Exception that should be raised."""

    exception: Exception


VersionInferenceResult = Union[
    VersionInferenceConfig,  # Proceed with inference
    VersionInferenceError,  # Show error/warning
    VersionInferenceException,  # Raise exception
    None,  # Don't infer (silent)
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
            if overrides is not None:
                # Clear version and proceed with overrides
                return VersionInferenceConfig(
                    dist_name=dist_name,
                    pyproject_data=pyproject_data,
                    overrides=overrides,
                )
            else:
                # Keep existing version from infer_version
                return None
        else:
            # Version set by something else
            return VersionInferenceError(
                f"version of {dist_name} already set", should_warn=True
            )

    # Handle setuptools-scm package
    if dist_name == "setuptools-scm":
        return None

    # Handle missing configuration
    if not pyproject_data.is_required and not pyproject_data.section_present:
        # If there are overrides, proceed with inference (explicit use_scm_version)
        if overrides is not None:
            return VersionInferenceConfig(
                dist_name=dist_name,
                pyproject_data=pyproject_data,
                overrides=overrides,
            )
        return None

    # Handle missing project section when required
    if (
        pyproject_data.is_required
        and not pyproject_data.section_present
        and not pyproject_data.project_present
    ):
        return None

    # All conditions met - proceed with inference
    return VersionInferenceConfig(
        dist_name=dist_name,
        pyproject_data=pyproject_data,
        overrides=overrides or {},
    )
