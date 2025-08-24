from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from setuptools_scm._integration.pyproject_reading import has_build_package_with_extra
from setuptools_scm._integration.pyproject_reading import read_pyproject


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


class TestBuildPackageWithExtra:
    """Test the has_build_package_with_extra function."""

    def test_has_simple_extra(self) -> None:
        """Test that simple extra is detected correctly."""
        requires = ["setuptools-scm[simple]"]
        assert (
            has_build_package_with_extra(requires, "setuptools-scm", "simple") is True
        )

    def test_has_no_simple_extra(self) -> None:
        """Test that missing simple extra is detected correctly."""
        requires = ["setuptools-scm"]
        assert (
            has_build_package_with_extra(requires, "setuptools-scm", "simple") is False
        )

    def test_has_different_extra(self) -> None:
        """Test that different extra is not detected as simple."""
        requires = ["setuptools-scm[toml]"]
        assert (
            has_build_package_with_extra(requires, "setuptools-scm", "simple") is False
        )

    def test_has_multiple_extras_including_simple(self) -> None:
        """Test that simple extra is detected when multiple extras are present."""
        requires = ["setuptools-scm[simple,toml]"]
        assert (
            has_build_package_with_extra(requires, "setuptools-scm", "simple") is True
        )

    def test_different_package_with_simple_extra(self) -> None:
        """Test that simple extra on different package is not detected."""
        requires = ["other-package[simple]"]
        assert (
            has_build_package_with_extra(requires, "setuptools-scm", "simple") is False
        )

    def test_version_specifier_with_extra(self) -> None:
        """Test that version specifiers work correctly with extras."""
        requires = ["setuptools-scm[simple]>=8.0"]
        assert (
            has_build_package_with_extra(requires, "setuptools-scm", "simple") is True
        )

    def test_complex_requirement_with_extra(self) -> None:
        """Test that complex requirements with extras work correctly."""
        requires = ["setuptools-scm[simple]>=8.0,<9.0"]
        assert (
            has_build_package_with_extra(requires, "setuptools-scm", "simple") is True
        )

    def test_empty_requires_list(self) -> None:
        """Test that empty requires list returns False."""
        requires: list[str] = []
        assert (
            has_build_package_with_extra(requires, "setuptools-scm", "simple") is False
        )

    def test_invalid_requirement_string(self) -> None:
        """Test that invalid requirement strings are handled gracefully."""
        requires = ["invalid requirement string"]
        assert (
            has_build_package_with_extra(requires, "setuptools-scm", "simple") is False
        )


def test_read_pyproject_with_given_definition(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that read_pyproject reads existing files correctly."""
    monkeypatch.setattr(
        "setuptools_scm._integration.pyproject_reading.read_toml_content",
        Mock(side_effect=FileNotFoundError("this test should not read")),
    )

    res = read_pyproject(
        _given_definition={
            "build-system": {"requires": ["setuptools-scm[simple]"]},
            "project": {"name": "test-package", "dynamic": ["version"]},
        }
    )

    assert res.should_infer()


def test_read_pyproject_with_setuptools_dynamic_version_warns() -> None:
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
