from __future__ import annotations

from pathlib import Path

import pytest

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
