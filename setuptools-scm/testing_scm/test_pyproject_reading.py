from __future__ import annotations

import configparser

from pathlib import Path
from unittest.mock import Mock

import pytest

from setuptools_scm._integration.pyproject_reading import has_build_package_with_extra
from setuptools_scm._integration.pyproject_reading import read_pyproject
from setuptools_scm._integration.pyproject_reading import should_infer


def parametrize_build_package_tests(ini_string: str) -> pytest.MarkDecorator:
    """Parametrize has_build_package_with_extra tests from INI string.

    Specific parser for testing build package requirements with extras.

    Parameters:
    - requires: multiline list of requirement strings
    - package_name: string
    - extra: string
    - expected: boolean (using ConfigParser's getboolean)
    """
    parser = configparser.ConfigParser()
    parser.read_string(ini_string)

    test_cases = []
    for section_name in parser.sections():
        section = parser[section_name]

        # Parse requires as list - split on newlines and strip
        requires_str = section.get("requires", "")
        requires = [line.strip() for line in requires_str.splitlines() if line.strip()]

        # Parse strings directly
        package_name = section.get("package_name")
        extra = section.get("extra")

        # Parse boolean using ConfigParser's native method
        expected = section.getboolean("expected")

        test_cases.append(
            pytest.param(requires, package_name, extra, expected, id=section_name)
        )

    return pytest.mark.parametrize(
        ("requires", "package_name", "extra", "expected"),
        test_cases,
    )


class TestPyProjectReading:
    """Test the pyproject reading functionality."""

    def test_read_pyproject_missing_file_raises(self, tmp_path: Path) -> None:
        """Test that read_pyproject raises FileNotFoundError when file is missing."""
        with pytest.raises(FileNotFoundError):
            read_pyproject(path=tmp_path / "nonexistent.toml")

    def test_read_pyproject_existing_file(self, tmp_path: Path) -> None:
        """Test that read_pyproject reads existing files correctly."""
        # Create a simple pyproject.toml
        pyproject_content = """
[build-system]
requires = ["setuptools>=80", "setuptools-scm>=8"]
build-backend = "setuptools.build_meta"

[project]
name = "test-package"
dynamic = ["version"]

[tool.setuptools_scm]
"""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(pyproject_content, encoding="utf-8")

        result = read_pyproject(path=pyproject_file)

        assert result.path == pyproject_file
        assert result.tool_name == "setuptools_scm"
        assert result.is_required is True
        assert result.section_present is True
        assert result.project_present is True
        assert result.project.get("name") == "test-package"


@parametrize_build_package_tests(
    """
    [has_simple_extra]
    requires =
        setuptools-scm[simple]
    package_name = setuptools-scm
    extra = simple
    expected = true

    [has_no_simple_extra]
    requires =
        setuptools-scm
    package_name = setuptools-scm
    extra = simple
    expected = false

    [has_different_extra]
    requires =
        setuptools-scm[toml]
    package_name = setuptools-scm
    extra = simple
    expected = false

    [has_multiple_extras_including_simple]
    requires =
        setuptools-scm[simple,toml]
    package_name = setuptools-scm
    extra = simple
    expected = true

    [different_package_with_simple_extra]
    requires =
        other-package[simple]
    package_name = setuptools-scm
    extra = simple
    expected = false

    [version_specifier_with_extra]
    requires =
        setuptools-scm[simple]>=8.0
    package_name = setuptools-scm
    extra = simple
    expected = true

    [complex_requirement_with_extra]
    requires =
        setuptools-scm[simple]>=8.0,<9.0
    package_name = setuptools-scm
    extra = simple
    expected = true

    [empty_requires_list]
    requires =
    package_name = setuptools-scm
    extra = simple
    expected = false

    [invalid_requirement_string]
    requires =
        invalid requirement string
    package_name = setuptools-scm
    extra = simple
    expected = false
    """
)
def test_has_build_package_with_extra(
    requires: list[str], package_name: str, extra: str, expected: bool
) -> None:
    """Test the has_build_package_with_extra function with various inputs."""
    assert has_build_package_with_extra(requires, package_name, extra) is expected


def test_read_pyproject_with_given_definition(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that read_pyproject reads existing files correctly."""
    monkeypatch.setattr(
        "vcs_versioning._toml.read_toml_content",
        Mock(side_effect=FileNotFoundError("this test should not read")),
    )

    res = read_pyproject(
        _given_definition={
            "build-system": {"requires": ["setuptools-scm[simple]"]},
            "project": {"name": "test-package", "dynamic": ["version"]},
        }
    )

    assert should_infer(res)


def test_read_pyproject_with_setuptools_dynamic_version_warns() -> None:
    """Test that warning is issued when version inference is enabled."""
    with pytest.warns(
        UserWarning,
        match=r"pyproject\.toml: at \[tool\.setuptools\.dynamic\]",
    ):
        pyproject_data = read_pyproject(
            _given_definition={
                "build-system": {"requires": ["setuptools-scm[simple]"]},
                "project": {"name": "test-package", "dynamic": ["version"]},
                "tool": {
                    "setuptools": {
                        "dynamic": {"version": {"attr": "test_package.__version__"}}
                    }
                },
            }
        )
    assert pyproject_data.project_version is None


def test_read_pyproject_with_setuptools_dynamic_version_no_warn_when_file_finder_only() -> (
    None
):
    """Test that no warning is issued when only file finder is used (no version inference)."""
    # When setuptools-scm is used only for file finding (no [tool.setuptools_scm] section,
    # no [simple] extra, version not in dynamic), it's valid to use tool.setuptools.dynamic.version
    import warnings

    with warnings.catch_warnings(record=True) as warning_list:
        warnings.simplefilter("always")
        pyproject_data = read_pyproject(
            _given_definition={
                "build-system": {"requires": ["setuptools-scm"]},
                "project": {"name": "test-package", "version": "1.0.0"},
                "tool": {
                    "setuptools": {
                        "dynamic": {"version": {"attr": "test_package.__version__"}}
                    }
                },
            }
        )

    # Filter to check for the dynamic version warning specifically
    relevant_warnings = [
        w for w in warning_list if "tool.setuptools.dynamic" in str(w.message)
    ]
    assert len(relevant_warnings) == 0, (
        "Should not warn about tool.setuptools.dynamic when only using file finder"
    )
    assert pyproject_data.project_version == "1.0.0"
    assert not should_infer(pyproject_data)
