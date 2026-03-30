"""Tests for issue #872: project_path config, discovery comparison, backward compat from root."""

from __future__ import annotations

from pathlib import Path

from vcs_versioning._backends._scm_workdir import ScmWorkdir
from vcs_versioning._config import Configuration


class TestProjectPathConfig:
    def test_default_is_none(self) -> None:
        config = Configuration()
        assert config.project_path is None

    def test_explicit_project_path(self) -> None:
        config = Configuration(project_path="python/modules/mymod")
        assert config.project_path == "python/modules/mymod"

    def test_bridge_from_root(self, tmp_path: Path) -> None:
        """When root is non-default and project_path is not set, derive project_path."""
        scm_root = tmp_path / "repo"
        scm_root.mkdir()
        project_dir = scm_root / "python" / "mymod"
        project_dir.mkdir(parents=True)
        pyproject = project_dir / "pyproject.toml"
        pyproject.write_text("[project]\n", encoding="utf-8")

        config = Configuration(
            relative_to=str(pyproject),
            root="../..",
        )
        assert config.project_path == "python/mymod"

    def test_no_bridge_when_root_is_default(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\n", encoding="utf-8")
        config = Configuration(relative_to=str(pyproject))
        assert config.project_path is None

    def test_explicit_project_path_skips_bridge(self, tmp_path: Path) -> None:
        scm_root = tmp_path / "repo"
        scm_root.mkdir()
        project_dir = scm_root / "sub"
        project_dir.mkdir()
        pyproject = project_dir / "pyproject.toml"
        pyproject.write_text("[project]\n", encoding="utf-8")

        config = Configuration(
            relative_to=str(pyproject),
            root="..",
            project_path="explicit/path",
        )
        assert config.project_path == "explicit/path"


class TestScmWorkdirProjectPath:
    def test_top_level_project(self, tmp_path: Path) -> None:
        wd = ScmWorkdir(path=tmp_path)
        assert wd.project_path == ""

    def test_nested_project(self, tmp_path: Path) -> None:
        project = tmp_path / "python" / "modules" / "mymod"
        project.mkdir(parents=True)
        wd = ScmWorkdir(path=tmp_path, project_root=project)
        assert wd.project_path == "python/modules/mymod"

    def test_single_level_nesting(self, tmp_path: Path) -> None:
        project = tmp_path / "mymod"
        project.mkdir()
        wd = ScmWorkdir(path=tmp_path, project_root=project)
        assert wd.project_path == "mymod"


class TestProjectPathVerification:
    """Test the comparison between config.project_path and workdir.project_path."""

    def test_matching_paths(self, tmp_path: Path) -> None:
        project = tmp_path / "sub" / "project"
        project.mkdir(parents=True)
        wd = ScmWorkdir(path=tmp_path, project_root=project)
        config = Configuration(project_path="sub/project")
        assert wd.project_path == config.project_path

    def test_none_config_accepts_any(self, tmp_path: Path) -> None:
        """When project_path is None, any discovered path is accepted."""
        project = tmp_path / "deep" / "nest"
        project.mkdir(parents=True)
        wd = ScmWorkdir(path=tmp_path, project_root=project)
        config = Configuration()  # project_path is None
        assert config.project_path is None
        assert wd.project_path == "deep/nest"

    def test_mismatch_detected(self, tmp_path: Path) -> None:
        project = tmp_path / "actual" / "location"
        project.mkdir(parents=True)
        wd = ScmWorkdir(path=tmp_path, project_root=project)
        config = Configuration(project_path="expected/location")
        assert wd.project_path != config.project_path
