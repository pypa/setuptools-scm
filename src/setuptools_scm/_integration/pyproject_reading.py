from __future__ import annotations

import warnings

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .. import _log
from .._requirement_cls import extract_package_name
from .toml import TOML_RESULT
from .toml import read_toml_content

log = _log.log.getChild("pyproject_reading")

_ROOT = "root"


@dataclass
class PyProjectData:
    path: Path
    tool_name: str
    project: TOML_RESULT
    section: TOML_RESULT
    is_required: bool
    section_present: bool
    project_present: bool

    @classmethod
    def for_testing(
        cls,
        is_required: bool = False,
        section_present: bool = False,
        project_present: bool = False,
        project_name: str | None = None,
    ) -> PyProjectData:
        """Create a PyProjectData instance for testing purposes."""
        if project_name is not None:
            project = {"name": project_name}
            assert project_present
        else:
            project = {}
        return cls(
            path=Path("pyproject.toml"),
            tool_name="setuptools_scm",
            project=project,
            section={},
            is_required=is_required,
            section_present=section_present,
            project_present=project_present,
        )

    @property
    def project_name(self) -> str | None:
        return self.project.get("name")

    def verify_dynamic_version_when_required(self) -> None:
        """Verify that dynamic=['version'] is set when setuptools-scm is used as build dependency indicator."""
        if self.is_required and not self.section_present:
            # When setuptools-scm is in build-system.requires but no tool section exists,
            # we need to verify that dynamic=['version'] is set in the project section
            # But only if there's actually a project section
            if not self.project_present:
                # No project section, so don't auto-activate setuptools_scm
                return
            dynamic = self.project.get("dynamic", [])
            if "version" not in dynamic:
                raise ValueError(
                    f"{self.path}: setuptools-scm is present in [build-system].requires "
                    f"but dynamic=['version'] is not set in [project]. "
                    f"Either add dynamic=['version'] to [project] or add a [tool.{self.tool_name}] section."
                )


def has_build_package(
    requires: Sequence[str], canonical_build_package_name: str
) -> bool:
    for requirement in requires:
        package_name = extract_package_name(requirement)
        if package_name == canonical_build_package_name:
            return True
    return False


def read_pyproject(
    path: Path = Path("pyproject.toml"),
    tool_name: str = "setuptools_scm",
    canonical_build_package_name: str = "setuptools-scm",
    missing_section_ok: bool = False,
    missing_file_ok: bool = False,
) -> PyProjectData:
    try:
        defn = read_toml_content(path)
    except FileNotFoundError:
        if missing_file_ok:
            log.warning("File %s not found, using empty configuration", path)
            return PyProjectData(
                path=path,
                tool_name=tool_name,
                project={},
                section={},
                is_required=False,
                section_present=False,
                project_present=False,
            )
        else:
            raise

    requires: list[str] = defn.get("build-system", {}).get("requires", [])
    is_required = has_build_package(requires, canonical_build_package_name)

    try:
        section = defn.get("tool", {})[tool_name]
        section_present = True
    except LookupError as e:
        if not is_required and not missing_section_ok:
            # Enhanced error message that mentions both configuration options
            error = (
                f"{path} does not contain a tool.{tool_name} section. "
                f"setuptools_scm requires configuration via either:\n"
                f"  1. [tool.{tool_name}] section in {path}, or\n"
                f"  2. {tool_name} (or setuptools-scm) in [build-system] requires"
            )
            raise LookupError(error) from e
        else:
            error = f"{path} does not contain a tool.{tool_name} section"
            log.warning("toml section missing %r", error, exc_info=True)
            section = {}
            section_present = False

    project = defn.get("project", {})
    project_present = "project" in defn
    pyproject_data = PyProjectData(
        path, tool_name, project, section, is_required, section_present, project_present
    )

    # Verify dynamic version when setuptools-scm is used as build dependency indicator
    pyproject_data.verify_dynamic_version_when_required()

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
