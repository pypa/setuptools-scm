"""Tests for integrator helper API."""

from __future__ import annotations

from pathlib import Path

import pytest
from vcs_versioning import PyProjectData, build_configuration_from_pyproject
from vcs_versioning._integrator_helpers import (
    build_configuration_from_pyproject_internal,
)


class TestPyProjectDataFromFile:
    """Test PyProjectData.from_file() public API."""

    def test_from_file_reads_vcs_versioning(self, tmp_path: Path) -> None:
        """Public API reads vcs-versioning section by default."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.vcs-versioning]
version_scheme = "guess-next-dev"
local_scheme = "no-local-version"
"""
        )

        data = PyProjectData.from_file(pyproject)

        assert data.tool_name == "vcs-versioning"
        assert data.section_present is True
        assert data.section["version_scheme"] == "guess-next-dev"
        assert data.section["local_scheme"] == "no-local-version"

    def test_from_file_ignores_setuptools_scm_by_default(self, tmp_path: Path) -> None:
        """Public API ignores setuptools_scm section without internal parameter."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.setuptools_scm]
version_scheme = "guess-next-dev"
"""
        )

        # Public API doesn't read setuptools_scm section
        data = PyProjectData.from_file(pyproject)
        assert data.section_present is False

    def test_from_file_internal_multi_tool_support(self, tmp_path: Path) -> None:
        """Internal _tool_names parameter supports multiple tools."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.setuptools_scm]
version_scheme = "guess-next-dev"
"""
        )

        # Internal API can use _tool_names
        data = PyProjectData.from_file(
            pyproject,
            _tool_names=["setuptools_scm", "vcs-versioning"],
        )

        assert data.tool_name == "setuptools_scm"
        assert data.section_present is True
        assert data.section["version_scheme"] == "guess-next-dev"

    def test_from_file_internal_tries_in_order(self, tmp_path: Path) -> None:
        """Internal API tries tool names in order."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.vcs-versioning]
local_scheme = "no-local-version"

[tool.setuptools_scm]
local_scheme = "node-and-date"
"""
        )

        # First tool name wins
        data = PyProjectData.from_file(
            pyproject,
            _tool_names=["setuptools_scm", "vcs-versioning"],
        )
        assert data.tool_name == "setuptools_scm"
        assert data.section["local_scheme"] == "node-and-date"

        # Order matters
        data2 = PyProjectData.from_file(
            pyproject,
            _tool_names=["vcs-versioning", "setuptools_scm"],
        )
        assert data2.tool_name == "vcs-versioning"
        assert data2.section["local_scheme"] == "no-local-version"


class TestManualPyProjectComposition:
    """Test manual PyProjectData composition by integrators."""

    def test_manual_composition_basic(self) -> None:
        """Integrators can manually compose PyProjectData."""
        pyproject = PyProjectData(
            path=Path("pyproject.toml"),
            tool_name="vcs-versioning",
            project={"name": "my-pkg"},
            section={"local_scheme": "no-local-version"},
            is_required=True,
            section_present=True,
            project_present=True,
            build_requires=["vcs-versioning"],
            definition={},
        )

        assert pyproject.tool_name == "vcs-versioning"
        assert pyproject.project_name == "my-pkg"
        assert pyproject.section["local_scheme"] == "no-local-version"

    def test_manual_composition_with_config_builder(self) -> None:
        """Manual composition works with config builder."""
        pyproject = PyProjectData(
            path=Path("pyproject.toml"),
            tool_name="vcs-versioning",
            project={"name": "test-pkg"},
            section={"version_scheme": "guess-next-dev"},
            is_required=False,
            section_present=True,
            project_present=True,
            build_requires=[],
            definition={},
        )

        config = build_configuration_from_pyproject(
            pyproject_data=pyproject,
            dist_name="test-pkg",
        )

        assert config.dist_name == "test-pkg"
        assert config.version_scheme == "guess-next-dev"


class TestBuildConfigurationFromPyProject:
    """Test build_configuration_from_pyproject() function."""

    def test_build_configuration_basic(self, tmp_path: Path) -> None:
        """Basic configuration building from pyproject data."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(
            """
[project]
name = "test-package"

[tool.vcs-versioning]
version_scheme = "guess-next-dev"
local_scheme = "no-local-version"
"""
        )

        pyproject = PyProjectData.from_file(pyproject_file)
        config = build_configuration_from_pyproject(
            pyproject_data=pyproject,
        )

        assert config.dist_name == "test-package"
        assert config.version_scheme == "guess-next-dev"
        assert config.local_scheme == "no-local-version"

    def test_build_configuration_with_dist_name_override(self, tmp_path: Path) -> None:
        """dist_name argument overrides project name."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(
            """
[project]
name = "wrong-name"

[tool.vcs-versioning]
version_scheme = "guess-next-dev"
"""
        )

        pyproject = PyProjectData.from_file(pyproject_file)
        config = build_configuration_from_pyproject(
            pyproject_data=pyproject,
            dist_name="correct-name",
        )

        assert config.dist_name == "correct-name"

    def test_build_configuration_with_integrator_overrides(
        self, tmp_path: Path
    ) -> None:
        """Integrator overrides override config file."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(
            """
[project]
name = "test-pkg"

[tool.vcs-versioning]
version_scheme = "guess-next-dev"
local_scheme = "node-and-date"
"""
        )

        pyproject = PyProjectData.from_file(pyproject_file)
        config = build_configuration_from_pyproject(
            pyproject_data=pyproject,
            # Integrator overrides
            local_scheme="no-local-version",
            version_scheme="semver-pep440-release-branch",
        )

        # Integrator overrides win over config file
        assert config.local_scheme == "no-local-version"
        assert config.version_scheme == "semver-pep440-release-branch"

    def test_build_configuration_with_env_overrides(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Env overrides win over integrator overrides."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(
            """
[project]
name = "test-pkg"

[tool.vcs-versioning]
local_scheme = "node-and-date"
"""
        )

        # Set environment TOML override
        monkeypatch.setenv(
            "VCS_VERSIONING_OVERRIDES",
            '{local_scheme = "no-local-version"}',
        )

        pyproject = PyProjectData.from_file(pyproject_file)
        config = build_configuration_from_pyproject(
            pyproject_data=pyproject,
            # Integrator tries to override, but env wins
            local_scheme="dirty-tag",
        )

        # Env override wins
        assert config.local_scheme == "no-local-version"


class TestOverridePriorityOrder:
    """Test complete priority order: env > integrator > config > defaults."""

    def test_priority_defaults_only(self, tmp_path: Path) -> None:
        """When nothing is set, use defaults."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(
            """
[project]
name = "test-pkg"

[tool.vcs-versioning]
"""
        )

        pyproject = PyProjectData.from_file(pyproject_file)
        config = build_configuration_from_pyproject(pyproject_data=pyproject)

        # Default values
        from vcs_versioning import DEFAULT_LOCAL_SCHEME, DEFAULT_VERSION_SCHEME

        assert config.local_scheme == DEFAULT_LOCAL_SCHEME
        assert config.version_scheme == DEFAULT_VERSION_SCHEME

    def test_priority_config_over_defaults(self, tmp_path: Path) -> None:
        """Config file overrides defaults."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(
            """
[project]
name = "test-pkg"

[tool.vcs-versioning]
local_scheme = "node-and-date"
"""
        )

        pyproject = PyProjectData.from_file(pyproject_file)
        config = build_configuration_from_pyproject(pyproject_data=pyproject)

        assert config.local_scheme == "node-and-date"

    def test_priority_integrator_over_config(self, tmp_path: Path) -> None:
        """Integrator overrides override config file."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(
            """
[project]
name = "test-pkg"

[tool.vcs-versioning]
local_scheme = "node-and-date"
"""
        )

        pyproject = PyProjectData.from_file(pyproject_file)
        config = build_configuration_from_pyproject(
            pyproject_data=pyproject,
            local_scheme="no-local-version",
        )

        assert config.local_scheme == "no-local-version"

    def test_priority_env_over_integrator(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Environment overrides win over integrator overrides."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(
            """
[project]
name = "test-pkg"

[tool.vcs-versioning]
local_scheme = "node-and-date"
"""
        )

        monkeypatch.setenv(
            "VCS_VERSIONING_OVERRIDES",
            '{local_scheme = "dirty-tag"}',
        )

        pyproject = PyProjectData.from_file(pyproject_file)
        config = build_configuration_from_pyproject(
            pyproject_data=pyproject,
            local_scheme="no-local-version",
        )

        # Env wins over everything
        assert config.local_scheme == "dirty-tag"

    def test_priority_complete_chain(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test complete priority chain with all levels."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(
            """
[project]
name = "test-pkg"

[tool.vcs-versioning]
local_scheme = "node-and-date"
version_scheme = "guess-next-dev"
"""
        )

        # Env only overrides local_scheme
        monkeypatch.setenv(
            "VCS_VERSIONING_OVERRIDES",
            '{local_scheme = "dirty-tag"}',
        )

        pyproject = PyProjectData.from_file(pyproject_file)
        config = build_configuration_from_pyproject(
            pyproject_data=pyproject,
            # Integrator overrides both
            local_scheme="no-local-version",
            version_scheme="semver-pep440-release-branch",
        )

        # local_scheme: env wins (dirty-tag)
        # version_scheme: integrator wins (no env override)
        assert config.local_scheme == "dirty-tag"
        assert config.version_scheme == "semver-pep440-release-branch"


class TestInternalAPIMultiTool:
    """Test internal API for setuptools_scm transition."""

    def test_internal_build_configuration_multi_tool(self, tmp_path: Path) -> None:
        """Internal API supports multiple tool names."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(
            """
[project]
name = "test-pkg"

[tool.setuptools_scm]
local_scheme = "no-local-version"
"""
        )

        # Internal API can load setuptools_scm section
        pyproject = PyProjectData.from_file(
            pyproject_file,
            _tool_names=["setuptools_scm", "vcs-versioning"],
        )

        # Internal helper can build configuration from it
        config = build_configuration_from_pyproject_internal(
            pyproject_data=pyproject,
            dist_name="test-pkg",
        )

        assert config.local_scheme == "no-local-version"
        assert config.dist_name == "test-pkg"

    def test_internal_prefers_first_tool_name(self, tmp_path: Path) -> None:
        """Internal API uses first available tool name."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(
            """
[tool.setuptools_scm]
local_scheme = "setuptools-value"

[tool.vcs-versioning]
local_scheme = "vcs-value"
"""
        )

        # setuptools_scm first
        pyproject1 = PyProjectData.from_file(
            pyproject_file,
            _tool_names=["setuptools_scm", "vcs-versioning"],
        )
        config1 = build_configuration_from_pyproject_internal(pyproject_data=pyproject1)
        assert config1.local_scheme == "setuptools-value"

        # vcs-versioning first
        pyproject2 = PyProjectData.from_file(
            pyproject_file,
            _tool_names=["vcs-versioning", "setuptools_scm"],
        )
        config2 = build_configuration_from_pyproject_internal(pyproject_data=pyproject2)
        assert config2.local_scheme == "vcs-value"


class TestDistNameResolution:
    """Test dist_name resolution in different scenarios."""

    def test_dist_name_from_argument(self, tmp_path: Path) -> None:
        """Explicit dist_name argument has highest priority."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(
            """
[project]
name = "project-name"

[tool.vcs-versioning]
"""
        )

        pyproject = PyProjectData.from_file(pyproject_file)
        config = build_configuration_from_pyproject(
            pyproject_data=pyproject,
            dist_name="argument-name",
        )

        # Argument wins
        assert config.dist_name == "argument-name"

    def test_dist_name_from_config(self, tmp_path: Path) -> None:
        """dist_name from config if no argument."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(
            """
[project]
name = "project-name"

[tool.vcs-versioning]
dist_name = "config-name"
"""
        )

        pyproject = PyProjectData.from_file(pyproject_file)
        config = build_configuration_from_pyproject(pyproject_data=pyproject)

        assert config.dist_name == "config-name"

    def test_dist_name_from_project(self, tmp_path: Path) -> None:
        """dist_name from project.name if not in config."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(
            """
[project]
name = "project-name"

[tool.vcs-versioning]
"""
        )

        pyproject = PyProjectData.from_file(pyproject_file)
        config = build_configuration_from_pyproject(pyproject_data=pyproject)

        assert config.dist_name == "project-name"

    def test_dist_name_none_when_missing(self, tmp_path: Path) -> None:
        """dist_name is None when not specified anywhere."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(
            """
[tool.vcs-versioning]
"""
        )

        pyproject = PyProjectData.from_file(pyproject_file)
        config = build_configuration_from_pyproject(pyproject_data=pyproject)

        assert config.dist_name is None


class TestEmptyPyProjectData:
    """Test with empty or minimal PyProjectData."""

    def test_empty_pyproject_section(self, tmp_path: Path) -> None:
        """Empty vcs-versioning section uses defaults."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(
            """
[tool.vcs-versioning]
"""
        )

        pyproject = PyProjectData.from_file(pyproject_file)
        config = build_configuration_from_pyproject(pyproject_data=pyproject)

        # Should use defaults
        from vcs_versioning import DEFAULT_LOCAL_SCHEME, DEFAULT_VERSION_SCHEME

        assert config.local_scheme == DEFAULT_LOCAL_SCHEME
        assert config.version_scheme == DEFAULT_VERSION_SCHEME

    def test_section_not_present(self, tmp_path: Path) -> None:
        """Missing section still creates configuration."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(
            """
[project]
name = "test-pkg"
"""
        )

        # Note: This will log a warning but should not fail
        pyproject = PyProjectData.from_file(pyproject_file)
        config = build_configuration_from_pyproject(
            pyproject_data=pyproject,
            dist_name="test-pkg",
        )

        # Should still create config with defaults
        assert config.dist_name == "test-pkg"
