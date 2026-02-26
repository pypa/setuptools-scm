from __future__ import annotations

import logging

from collections.abc import Sequence
from pathlib import Path

from vcs_versioning._pyproject_reading import DEFAULT_PYPROJECT_PATH
from vcs_versioning._pyproject_reading import GivenPyProjectResult
from vcs_versioning._pyproject_reading import PyProjectData
from vcs_versioning._pyproject_reading import get_args_for_pyproject
from vcs_versioning._pyproject_reading import read_pyproject as _vcs_read_pyproject
from vcs_versioning._requirement_cls import Requirement
from vcs_versioning._requirement_cls import extract_package_name
from vcs_versioning._toml import TOML_RESULT

log = logging.getLogger(__name__)

_ROOT = "root"

__all__ = [
    "PyProjectData",
    "get_args_for_pyproject",
    "has_build_package_with_extra",
    "read_pyproject",
    "should_infer",
]


def should_infer(pyproject_data: PyProjectData) -> bool:
    """
    Determine if setuptools_scm should infer version based on configuration.

    Infer when:
    1. An explicit [tool.setuptools_scm] section is present, OR
    2. setuptools-scm[simple] is in build-system.requires AND
       version is in project.dynamic

    Args:
        pyproject_data: The PyProjectData instance to check

    Returns:
        True if version should be inferred, False otherwise
    """
    # Original behavior: explicit tool section
    if pyproject_data.section_present:
        return True

    # New behavior: simple extra + dynamic version
    if pyproject_data.project_present:
        dynamic_fields = pyproject_data.project.get("dynamic", [])
        if "version" in dynamic_fields:
            if has_build_package_with_extra(
                pyproject_data.build_requires, "setuptools-scm", "simple"
            ):
                return True

    return False


def has_build_package_with_extra(
    requires: Sequence[str], canonical_build_package_name: str, extra_name: str
) -> bool:
    """Check if a build dependency has a specific extra.

    Args:
        requires: List of requirement strings from build-system.requires
        canonical_build_package_name: The canonical package name to look for
        extra_name: The extra name to check for (e.g., "simple")

    Returns:
        True if the package is found with the specified extra
    """
    for requirement_string in requires:
        try:
            requirement = Requirement(requirement_string)
            package_name = extract_package_name(requirement_string)
            if package_name == canonical_build_package_name:
                if extra_name in requirement.extras:
                    return True
        except Exception:
            # If parsing fails, continue to next requirement
            continue
    return False


def _check_setuptools_dynamic_version_conflict(
    path: Path, pyproject_data: PyProjectData
) -> None:
    """Warn if tool.setuptools.dynamic.version conflicts with setuptools-scm.

    Only warns if setuptools-scm is being used for version inference (not just file finding).
    When only file finders are used, it's valid to use tool.setuptools.dynamic.version.
    """
    # Only warn if setuptools-scm is performing version inference
    if not should_infer(pyproject_data):
        return

    # Check if tool.setuptools.dynamic.version exists
    tool = pyproject_data.definition.get("tool", {})
    if not isinstance(tool, dict):
        return

    setuptools_config = tool.get("setuptools", {})
    if not isinstance(setuptools_config, dict):
        return

    dynamic_config = setuptools_config.get("dynamic", {})
    if not isinstance(dynamic_config, dict):
        return

    if "version" in dynamic_config:
        from .deprecation import warn_pyproject_setuptools_dynamic_version

        warn_pyproject_setuptools_dynamic_version(path)


def read_pyproject(
    path: Path = DEFAULT_PYPROJECT_PATH,
    tool_name: str = "setuptools_scm",
    canonical_build_package_name: str = "setuptools-scm",
    _given_result: GivenPyProjectResult = None,
    _given_definition: TOML_RESULT | None = None,
) -> PyProjectData:
    """Read and parse pyproject configuration with setuptools-specific extensions.

    This wraps vcs_versioning's read_pyproject and adds setuptools-specific behavior.
    Uses internal multi-tool support to read both setuptools_scm and vcs-versioning sections.
    """
    # Use vcs_versioning's reader with multi-tool support (internal API)
    # This allows setuptools_scm to transition to vcs-versioning section
    pyproject_data = _vcs_read_pyproject(
        path,
        canonical_build_package_name=canonical_build_package_name,
        _given_result=_given_result,
        _given_definition=_given_definition,
        tool_names=[
            "setuptools_scm",
            "vcs-versioning",
        ],  # Try both, setuptools_scm first
    )

    # Check for conflicting tool.setuptools.dynamic configuration
    # Use the definition from pyproject_data (read by vcs_versioning)
    _check_setuptools_dynamic_version_conflict(path, pyproject_data)

    return pyproject_data
