from __future__ import annotations

import logging

from pathlib import Path
from typing import Sequence

from vcs_versioning._pyproject_reading import DEFAULT_PYPROJECT_PATH
from vcs_versioning._pyproject_reading import DEFAULT_TOOL_NAME
from vcs_versioning._pyproject_reading import PyProjectData as _VcsPyProjectData
from vcs_versioning._pyproject_reading import (
    get_args_for_pyproject as _vcs_get_args_for_pyproject,
)
from vcs_versioning._pyproject_reading import read_pyproject as _vcs_read_pyproject
from vcs_versioning._requirement_cls import Requirement
from vcs_versioning._requirement_cls import extract_package_name
from vcs_versioning._toml import TOML_RESULT

from .. import _types as _t

log = logging.getLogger(__name__)

_ROOT = "root"


# Extend PyProjectData with setuptools-specific methods
class PyProjectData(_VcsPyProjectData):
    """Extended PyProjectData with setuptools-specific functionality"""

    def should_infer(self) -> bool:
        """
        Determine if setuptools_scm should infer version based on configuration.

        Infer when:
        1. An explicit [tool.setuptools_scm] section is present, OR
        2. setuptools-scm[simple] is in build-system.requires AND
           version is in project.dynamic

        Returns:
            True if [tool.setuptools_scm] is present, otherwise False
        """
        # Original behavior: explicit tool section
        if self.section_present:
            return True

        # New behavior: simple extra + dynamic version
        if self.project_present:
            dynamic_fields = self.project.get("dynamic", [])
            if "version" in dynamic_fields:
                if has_build_package_with_extra(
                    self.build_requires, "setuptools-scm", "simple"
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


def read_pyproject(
    path: Path = DEFAULT_PYPROJECT_PATH,
    tool_name: str = DEFAULT_TOOL_NAME,
    canonical_build_package_name: str = "setuptools-scm",
    _given_result: _t.GivenPyProjectResult = None,
    _given_definition: TOML_RESULT | None = None,
) -> PyProjectData:
    """Read and parse pyproject configuration with setuptools-specific extensions.

    This wraps vcs_versioning's read_pyproject and adds setuptools-specific behavior.
    """
    # Use vcs_versioning's reader
    vcs_data = _vcs_read_pyproject(
        path, tool_name, canonical_build_package_name, _given_result, _given_definition
    )

    # Convert to setuptools-extended PyProjectData
    return PyProjectData(
        path=vcs_data.path,
        tool_name=vcs_data.tool_name,
        project=vcs_data.project,
        section=vcs_data.section,
        is_required=vcs_data.is_required,
        section_present=vcs_data.section_present,
        project_present=vcs_data.project_present,
        build_requires=vcs_data.build_requires,
    )


def get_args_for_pyproject(
    pyproject: PyProjectData,
    dist_name: str | None,
    kwargs: TOML_RESULT,
) -> TOML_RESULT:
    """Delegate to vcs_versioning's implementation"""
    return _vcs_get_args_for_pyproject(pyproject, dist_name, kwargs)
