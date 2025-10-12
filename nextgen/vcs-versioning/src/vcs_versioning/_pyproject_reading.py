"""Core pyproject.toml reading functionality"""

from __future__ import annotations

import logging
import warnings

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from . import _types as _t
from ._requirement_cls import extract_package_name
from ._toml import TOML_RESULT
from ._toml import InvalidTomlError
from ._toml import read_toml_content

log = logging.getLogger(__name__)

_ROOT = "root"


DEFAULT_PYPROJECT_PATH = Path("pyproject.toml")
DEFAULT_TOOL_NAME = "setuptools_scm"  # For backward compatibility


@dataclass
class PyProjectData:
    """Core pyproject.toml data structure"""

    path: Path
    tool_name: str
    project: TOML_RESULT
    section: TOML_RESULT
    is_required: bool
    section_present: bool
    project_present: bool
    build_requires: list[str]

    @classmethod
    def for_testing(
        cls,
        *,
        is_required: bool = False,
        section_present: bool = False,
        project_present: bool = False,
        project_name: str | None = None,
        has_dynamic_version: bool = True,
        build_requires: list[str] | None = None,
        local_scheme: str | None = None,
    ) -> PyProjectData:
        """Create a PyProjectData instance for testing purposes."""
        project: TOML_RESULT
        if project_name is not None:
            project = {"name": project_name}
            assert project_present
        else:
            project = {}

        # If project is present and has_dynamic_version is True, add dynamic=['version']
        if project_present and has_dynamic_version:
            project["dynamic"] = ["version"]

        if build_requires is None:
            build_requires = []
        if local_scheme is not None:
            assert section_present
            section = {"local_scheme": local_scheme}
        else:
            section = {}
        return cls(
            path=DEFAULT_PYPROJECT_PATH,
            tool_name=DEFAULT_TOOL_NAME,
            project=project,
            section=section,
            is_required=is_required,
            section_present=section_present,
            project_present=project_present,
            build_requires=build_requires,
        )

    @classmethod
    def empty(
        cls, path: Path = DEFAULT_PYPROJECT_PATH, tool_name: str = DEFAULT_TOOL_NAME
    ) -> PyProjectData:
        return cls(
            path=path,
            tool_name=tool_name,
            project={},
            section={},
            is_required=False,
            section_present=False,
            project_present=False,
            build_requires=[],
        )

    @property
    def project_name(self) -> str | None:
        return self.project.get("name")

    @property
    def project_version(self) -> str | None:
        """Return the static version from [project] if present.

        When the project declares dynamic = ["version"], the version
        is intentionally omitted from [project] and this returns None.
        """
        return self.project.get("version")


def has_build_package(
    requires: Sequence[str], canonical_build_package_name: str
) -> bool:
    """Check if a package is in build requirements."""
    for requirement in requires:
        package_name = extract_package_name(requirement)
        if package_name == canonical_build_package_name:
            return True
    return False


def read_pyproject(
    path: Path = DEFAULT_PYPROJECT_PATH,
    tool_name: str = DEFAULT_TOOL_NAME,
    canonical_build_package_name: str = "setuptools-scm",
    _given_result: _t.GivenPyProjectResult = None,
    _given_definition: TOML_RESULT | None = None,
) -> PyProjectData:
    """Read and parse pyproject configuration.

    This function supports dependency injection for tests via ``_given_result``
    and ``_given_definition``.

    :param path: Path to the pyproject file
    :param tool_name: The tool section name (default: ``setuptools_scm``)
    :param canonical_build_package_name: Normalized build requirement name
    :param _given_result: Optional testing hook. Can be:
        - ``PyProjectData``: returned directly
        - ``InvalidTomlError`` | ``FileNotFoundError``: raised directly
        - ``None``: read from filesystem (default)
    :param _given_definition: Optional testing hook to provide parsed TOML content.
        When provided, this dictionary is used instead of reading and parsing
        the file from disk. Ignored if ``_given_result`` is provided.
    """

    if _given_result is not None:
        if isinstance(_given_result, PyProjectData):
            return _given_result
        if isinstance(_given_result, (InvalidTomlError, FileNotFoundError)):
            raise _given_result

    if _given_definition is not None:
        defn = _given_definition
    else:
        defn = read_toml_content(path)

    requires: list[str] = defn.get("build-system", {}).get("requires", [])
    is_required = has_build_package(requires, canonical_build_package_name)

    tool_section = defn.get("tool", {})

    # Support both [tool.vcs-versioning] and [tool.setuptools_scm] for backward compatibility
    section = {}
    section_present = False
    actual_tool_name = tool_name

    # Try vcs-versioning first, then setuptools_scm for backward compat
    for name in ["vcs-versioning", "setuptools_scm"]:
        if name in tool_section:
            section = tool_section[name]
            section_present = True
            actual_tool_name = name
            break

    if not section_present:
        log.warning(
            "toml section missing %r does not contain a tool.%s section",
            path,
            tool_name,
        )

    project = defn.get("project", {})
    project_present = "project" in defn

    pyproject_data = PyProjectData(
        path,
        actual_tool_name,
        project,
        section,
        is_required,
        section_present,
        project_present,
        requires,
    )

    return pyproject_data


def get_args_for_pyproject(
    pyproject: PyProjectData,
    dist_name: str | None,
    kwargs: TOML_RESULT,
) -> TOML_RESULT:
    """drops problematic details and figures the distribution name"""
    section = pyproject.section.copy()
    kwargs = kwargs.copy()
    if "relative_to" in section:
        relative = section.pop("relative_to")
        warnings.warn(
            f"{pyproject.path}: at [tool.{pyproject.tool_name}]\n"
            f"ignoring value relative_to={relative!r}"
            " as its always relative to the config file"
        )
    if "dist_name" in section:
        if dist_name is None:
            dist_name = section.pop("dist_name")
        else:
            assert dist_name == section["dist_name"]
            section.pop("dist_name")
    if dist_name is None:
        # minimal pep 621 support for figuring the pretend keys
        dist_name = pyproject.project_name
    if _ROOT in kwargs:
        if kwargs[_ROOT] is None:
            kwargs.pop(_ROOT, None)
        elif _ROOT in section:
            if section[_ROOT] != kwargs[_ROOT]:
                warnings.warn(
                    f"root {section[_ROOT]} is overridden"
                    f" by the cli arg {kwargs[_ROOT]}"
                )
            section.pop(_ROOT, None)
    return {"dist_name": dist_name, **section, **kwargs}
