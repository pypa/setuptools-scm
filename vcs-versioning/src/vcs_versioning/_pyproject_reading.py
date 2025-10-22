"""Core pyproject.toml reading functionality"""

from __future__ import annotations

import logging
import os
import sys
import warnings
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from ._requirement_cls import extract_package_name
from ._toml import TOML_RESULT, InvalidTomlError, read_toml_content

log = logging.getLogger(__name__)

_ROOT = "root"


DEFAULT_PYPROJECT_PATH = Path("pyproject.toml")

# Testing injection type for configuration reading
GivenPyProjectResult: TypeAlias = (
    "PyProjectData" | InvalidTomlError | FileNotFoundError | None
)


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
    definition: TOML_RESULT

    @classmethod
    def for_testing(
        cls,
        *,
        tool_name: str,
        is_required: bool = False,
        section_present: bool = False,
        project_present: bool = False,
        project_name: str | None = None,
        has_dynamic_version: bool = True,
        build_requires: list[str] | None = None,
        local_scheme: str | None = None,
    ) -> Self:
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
            tool_name=tool_name,
            project=project,
            section=section,
            is_required=is_required,
            section_present=section_present,
            project_present=project_present,
            build_requires=build_requires,
            definition={},
        )

    @classmethod
    def empty(cls, tool_name: str, path: Path = DEFAULT_PYPROJECT_PATH) -> Self:
        return cls(
            path=path,
            tool_name=tool_name,
            project={},
            section={},
            is_required=False,
            section_present=False,
            project_present=False,
            build_requires=[],
            definition={},
        )

    @classmethod
    def from_file(
        cls,
        path: str | os.PathLike[str] = "pyproject.toml",
        *,
        _tool_names: list[str] | None = None,
    ) -> Self:
        """Load PyProjectData from pyproject.toml.

        Public API: reads tool.vcs-versioning section.
        Internal use: pass _tool_names for multi-tool support (e.g., setuptools_scm transition).

        Args:
            path: Path to pyproject.toml file
            _tool_names: Internal parameter for multi-tool support.
                        If None, uses ["vcs-versioning"] (public API behavior).

        Returns:
            PyProjectData instance loaded from file

        Raises:
            FileNotFoundError: If pyproject.toml not found
            InvalidTomlError: If pyproject.toml has invalid TOML syntax

        Example:
            >>> # Public API usage
            >>> pyproject = PyProjectData.from_file("pyproject.toml")
            >>>
            >>> # Internal usage (setuptools_scm transition)
            >>> pyproject = PyProjectData.from_file(
            ...     "pyproject.toml",
            ...     _tool_names=["setuptools_scm", "vcs-versioning"]
            ... )
        """
        if _tool_names is None:
            # Public API path - only vcs-versioning
            _tool_names = ["vcs-versioning"]

        result = read_pyproject(Path(path), tool_names=_tool_names)
        # Type narrowing for mypy: read_pyproject returns PyProjectData,
        # but subclasses (like setuptools_scm's extended version) need Self
        return result  # type: ignore[return-value]

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
    canonical_build_package_name: str = "setuptools-scm",
    _given_result: GivenPyProjectResult = None,
    _given_definition: TOML_RESULT | None = None,
    tool_names: list[str] | None = None,
) -> PyProjectData:
    """Read and parse pyproject configuration.

    This function supports dependency injection for tests via ``_given_result``
    and ``_given_definition``.

    :param path: Path to the pyproject file
    :param canonical_build_package_name: Normalized build requirement name
    :param _given_result: Optional testing hook. Can be:
        - ``PyProjectData``: returned directly
        - ``InvalidTomlError`` | ``FileNotFoundError``: raised directly
        - ``None``: read from filesystem (default)
    :param _given_definition: Optional testing hook to provide parsed TOML content.
        When provided, this dictionary is used instead of reading and parsing
        the file from disk. Ignored if ``_given_result`` is provided.
    :param tool_names: List of tool section names to try in order.
        If None, defaults to ["vcs-versioning", "setuptools_scm"]
    """

    if _given_result is not None:
        if isinstance(_given_result, PyProjectData):
            return _given_result
        if isinstance(_given_result, InvalidTomlError | FileNotFoundError):
            raise _given_result

    if _given_definition is not None:
        defn = _given_definition
    else:
        defn = read_toml_content(path)

    requires: list[str] = defn.get("build-system", {}).get("requires", [])
    is_required = has_build_package(requires, canonical_build_package_name)

    tool_section = defn.get("tool", {})

    # Determine which tool names to try
    if tool_names is None:
        # Default: try vcs-versioning first, then setuptools_scm for backward compat
        tool_names = ["vcs-versioning", "setuptools_scm"]

    # Try each tool name in order
    section = {}
    section_present = False
    actual_tool_name = tool_names[0] if tool_names else "vcs-versioning"

    for name in tool_names:
        if name in tool_section:
            section = tool_section[name]
            section_present = True
            actual_tool_name = name
            break

    if not section_present:
        log.warning(
            "toml section missing %r does not contain any of the tool sections: %s",
            path,
            tool_names,
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
        defn,
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
            " as its always relative to the config file",
            stacklevel=2,
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
                    f" by the cli arg {kwargs[_ROOT]}",
                    stacklevel=2,
                )
            section.pop(_ROOT, None)
    return {"dist_name": dist_name, **section, **kwargs}
