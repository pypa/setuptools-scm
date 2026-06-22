"""Tests for workdir discovery probing, marker ordering, project_path verification."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from vcs_versioning._backends._scm_workdir import ScmWorkdir
from vcs_versioning._config import Configuration
from vcs_versioning._fallback_workdir import (
    ArchivedWorkdir,
    MetadataWorkdir,
    PkgInfoWorkdir,
    StaticWorkdir,
)
from vcs_versioning._scm_metadata import (
    ScmVersionData,
    write_scm_file_list,
    write_scm_version_data,
)
from vcs_versioning._worktree_discovery import discover_workdir


def _git_init(path: Path) -> None:
    """Initialize a git repo at *path* with an initial commit."""
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    (path / "dummy").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init", "--allow-empty"],
        cwd=path,
        check=True,
        capture_output=True,
    )


class TestDiscoverWorkdirGit:
    def test_discovers_git_repo(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        config = Configuration(relative_to=str(tmp_path / "pyproject.toml"))
        result = discover_workdir(config)
        assert result is not None
        assert isinstance(result, ScmWorkdir)
        assert result.path == tmp_path

    def test_discovers_git_repo_nested_project(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        project = tmp_path / "sub" / "pkg"
        project.mkdir(parents=True)
        pyproject = project / "pyproject.toml"
        pyproject.write_text("[project]\n", encoding="utf-8")
        config = Configuration(
            relative_to=str(pyproject),
            root="../..",
        )
        result = discover_workdir(config)
        assert result is not None
        assert isinstance(result, ScmWorkdir)
        assert result.path == tmp_path
        assert result.project_root == project
        assert result.project_path == "sub/pkg"

    def test_search_parent_directories(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        subdir = tmp_path / "deep" / "nested"
        subdir.mkdir(parents=True)
        config = Configuration(
            relative_to=str(subdir / "pyproject.toml"),
            search_parent_directories=True,
        )
        result = discover_workdir(config)
        assert result is not None
        assert isinstance(result, ScmWorkdir)
        assert result.path == tmp_path


class TestDiscoverWorkdirFallback:
    def test_discovers_pkginfo(self, tmp_path: Path) -> None:
        (tmp_path / "PKG-INFO").write_text(
            "Metadata-Version: 2.1\nName: pkg\nVersion: 3.0.0\n",
            encoding="utf-8",
        )
        config = Configuration(relative_to=str(tmp_path / "pyproject.toml"))
        result = discover_workdir(config)
        assert result is not None
        assert isinstance(result, PkgInfoWorkdir)

    def test_discovers_git_archival(self, tmp_path: Path) -> None:
        (tmp_path / ".git_archival.txt").write_text(
            "node: abc1234\nref-names: HEAD\n",
            encoding="utf-8",
        )
        config = Configuration(relative_to=str(tmp_path / "pyproject.toml"))
        result = discover_workdir(config)
        assert result is not None
        assert isinstance(result, ArchivedWorkdir)

    def test_discovers_hg_archival(self, tmp_path: Path) -> None:
        (tmp_path / ".hg_archival.txt").write_text(
            "repo: abc123\nnode: def456\n",
            encoding="utf-8",
        )
        config = Configuration(relative_to=str(tmp_path / "pyproject.toml"))
        result = discover_workdir(config)
        assert result is not None
        assert isinstance(result, ArchivedWorkdir)

    def test_scm_preferred_over_fallback(self, tmp_path: Path) -> None:
        """SCM markers should be preferred over fallback markers."""
        _git_init(tmp_path)
        (tmp_path / "PKG-INFO").write_text(
            "Metadata-Version: 2.1\nName: pkg\nVersion: 3.0.0\n",
            encoding="utf-8",
        )
        config = Configuration(relative_to=str(tmp_path / "pyproject.toml"))
        result = discover_workdir(config)
        assert result is not None
        assert isinstance(result, ScmWorkdir)

    def test_static_fallback_with_fallback_version(self, tmp_path: Path) -> None:
        config = Configuration(
            relative_to=str(tmp_path / "pyproject.toml"),
            fallback_version="99.0.0",
        )
        result = discover_workdir(config)
        assert result is not None
        assert isinstance(result, StaticWorkdir)

    def test_returns_none_when_nothing_found(self, tmp_path: Path) -> None:
        config = Configuration(relative_to=str(tmp_path / "pyproject.toml"))
        result = discover_workdir(config)
        assert result is None


class TestProjectPathVerificationInDiscovery:
    def test_matching_project_path(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        project = tmp_path / "sub"
        project.mkdir()
        pyproject = project / "pyproject.toml"
        pyproject.write_text("[project]\n", encoding="utf-8")
        config = Configuration(
            relative_to=str(pyproject),
            root="..",
            project_path="sub",
        )
        result = discover_workdir(config)
        assert result is not None
        assert isinstance(result, ScmWorkdir)
        assert result.project_path == "sub"

    def test_mismatched_project_path_raises(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        project = tmp_path / "actual"
        project.mkdir()
        pyproject = project / "pyproject.toml"
        pyproject.write_text("[project]\n", encoding="utf-8")
        config = Configuration(
            relative_to=str(pyproject),
            root="..",
            project_path="wrong/path",
        )
        with pytest.raises(ValueError, match="project_path mismatch"):
            discover_workdir(config)


class TestFallbackPriority:
    @pytest.mark.issue(1431)
    def test_unprocessed_archival_falls_through_to_pkginfo(
        self, tmp_path: Path
    ) -> None:
        """Unprocessed .git_archival.txt must not shadow a valid PKG-INFO.

        PyPI sdists contain both files: a .git_archival.txt with raw
        ``$Format:...`` placeholders (never substituted because the sdist
        was built by setuptools, not ``git archive``) and a PKG-INFO with
        the correct version.  Before the fix, the archival fallback was
        stashed as the sole candidate and its ``get_scm_version()`` returned
        None, causing a LookupError.
        """
        (tmp_path / ".git_archival.txt").write_text(
            "node: $Format:%H$\n"
            "node-date: $Format:%cI$\n"
            "describe-name: $Format:%(describe:tags=true)$\n"
            "ref-names: $Format:%D$\n",
            encoding="utf-8",
        )
        (tmp_path / "PKG-INFO").write_text(
            "Metadata-Version: 2.1\nName: my-pkg\nVersion: 1.2.3\n",
            encoding="utf-8",
        )
        config = Configuration(relative_to=str(tmp_path / "pyproject.toml"))
        result = discover_workdir(config)
        assert result is not None
        assert isinstance(result, PkgInfoWorkdir)
        version = result.get_scm_version()
        assert version is not None
        assert str(version.tag) == "1.2.3"


class TestFallbackWorkdirDiscoveryFactories:
    def test_discover_archival_git(self, tmp_path: Path) -> None:
        from vcs_versioning._fallback_workdir import discover_archival

        (tmp_path / ".git_archival.txt").write_text("node: abc\n", encoding="utf-8")
        config = Configuration()
        result = discover_archival(tmp_path, config=config)
        assert result is not None
        assert isinstance(result, ArchivedWorkdir)

    def test_discover_archival_hg(self, tmp_path: Path) -> None:
        from vcs_versioning._fallback_workdir import discover_archival

        (tmp_path / ".hg_archival.txt").write_text("node: abc\n", encoding="utf-8")
        config = Configuration()
        result = discover_archival(tmp_path, config=config)
        assert result is not None
        assert isinstance(result, ArchivedWorkdir)

    def test_discover_archival_none(self, tmp_path: Path) -> None:
        from vcs_versioning._fallback_workdir import discover_archival

        config = Configuration()
        assert discover_archival(tmp_path, config=config) is None


class TestMetadataWorkdir:
    def test_reads_version_from_json(self, tmp_path: Path) -> None:
        data = ScmVersionData(
            tag="2.0.0",
            distance=3,
            node="gabc1234",
            dirty=False,
            branch="main",
            node_date="2024-06-15",
        )
        write_scm_version_data(tmp_path, data)
        write_scm_file_list(tmp_path, ["src/pkg/__init__.py"])

        config = Configuration()
        wd = MetadataWorkdir(path=tmp_path, metadata_dir=tmp_path, _config=config)
        version = wd.get_scm_version()
        assert version is not None
        assert str(version.tag) == "2.0.0"
        assert version.distance == 3
        assert version.node == "gabc1234"

        files = wd.list_tracked_files()
        assert files == ["src/pkg/__init__.py"]

    def test_missing_metadata_returns_none(self, tmp_path: Path) -> None:
        config = Configuration()
        wd = MetadataWorkdir(path=tmp_path, metadata_dir=tmp_path, _config=config)
        assert wd.get_scm_version() is None
        assert wd.list_tracked_files() == []
