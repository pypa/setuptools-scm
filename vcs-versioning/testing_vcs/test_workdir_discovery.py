"""Tests for workdir discovery probing, marker ordering, project_path verification."""

from __future__ import annotations

import subprocess
from importlib.metadata import EntryPoint
from pathlib import Path
from typing import Any

import pytest
from vcs_versioning._backends._scm_workdir import ScmWorkdir
from vcs_versioning._config import Configuration
from vcs_versioning._fallback_workdir import (
    ArchivedWorkdir,
    FallbackWorkdir,
    MetadataWorkdir,
    PkgInfoWorkdir,
    StaticWorkdir,
)
from vcs_versioning._scm_metadata import (
    ScmVersionData,
    write_scm_file_list,
    write_scm_version_data,
)
from vcs_versioning._scm_version import ScmVersion, meta
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

    @pytest.mark.issue(1440)
    def test_list_tracked_files_scoped_to_project_root(self, tmp_path: Path) -> None:
        """In a monorepo, list_tracked_files() must only return files under project_root."""
        # Resolve to real path to avoid Windows 8.3 short name mismatches
        tmp_path = tmp_path.resolve()
        _git_init(tmp_path)

        # Create files in two sibling projects
        proj_a = tmp_path / "project-a"
        proj_b = tmp_path / "project-b"
        proj_a.mkdir()
        proj_b.mkdir()
        (proj_a / "a.py").write_text("# a", encoding="utf-8")
        (proj_b / "b.py").write_text("# b", encoding="utf-8")

        subprocess.run(
            ["git", "add", "."], cwd=tmp_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "add projects"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Discover from project-a with root=".." (monorepo pattern)
        config = Configuration(
            relative_to=str(proj_a / "pyproject.toml"),
            root="..",
        )
        result = discover_workdir(config)
        assert result is not None
        assert isinstance(result, ScmWorkdir)
        assert result.path == tmp_path
        assert result.project_root == proj_a

        files = list(result.list_tracked_files())
        # Should only contain files under project-a, not project-b or repo root
        assert any("a.py" in f for f in files), f"expected a.py in {files}"
        assert not any("b.py" in f for f in files), f"unexpected b.py in {files}"
        assert not any("dummy" in f for f in files), f"unexpected dummy in {files}"


class TestDiscoverWorkdirFallback:
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

    def test_discovers_pkginfo(self, tmp_path: Path) -> None:
        (tmp_path / "PKG-INFO").write_text(
            "Metadata-Version: 2.1\nName: pkg\nVersion: 3.0.0\n",
            encoding="utf-8",
        )
        config = Configuration(relative_to=str(tmp_path / "pyproject.toml"))
        result = discover_workdir(config)
        assert result is not None
        assert isinstance(result, PkgInfoWorkdir)

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

    def test_discover_pkginfo(self, tmp_path: Path) -> None:
        from vcs_versioning._fallback_workdir import discover_pkginfo

        (tmp_path / "PKG-INFO").write_text("Version: 1.0\n", encoding="utf-8")
        config = Configuration()
        result = discover_pkginfo(tmp_path, config=config)
        assert result is not None
        assert isinstance(result, PkgInfoWorkdir)

    def test_discover_pkginfo_none(self, tmp_path: Path) -> None:
        from vcs_versioning._fallback_workdir import discover_pkginfo

        config = Configuration()
        assert discover_pkginfo(tmp_path, config=config) is None


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

    @pytest.mark.issue(1439)
    def test_custom_tag_regex_does_not_break_metadata(self, tmp_path: Path) -> None:
        """Stored tags are already parsed; custom tag_regex must not re-parse them."""
        data = ScmVersionData(
            tag="1.5.5",
            distance=0,
            node="gabc1234",
            dirty=False,
            branch="main",
            node_date=None,
        )
        write_scm_version_data(tmp_path, data)

        config = Configuration(
            tag_regex=r"^cuda-pathfinder-(?P<version>v\d+\.\d+\.\d+(?:[ab]\d+)?)",
        )
        wd = MetadataWorkdir(path=tmp_path, metadata_dir=tmp_path, _config=config)
        version = wd.get_scm_version()
        assert version is not None
        assert str(version.tag) == "1.5.5"

    def test_missing_metadata_returns_none(self, tmp_path: Path) -> None:
        config = Configuration()
        wd = MetadataWorkdir(path=tmp_path, metadata_dir=tmp_path, _config=config)
        assert wd.get_scm_version() is None
        assert wd.list_tracked_files() == []


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


class TestPkgInfoRegisteredByCore:
    """PKG-INFO fallback must work without setuptools-scm installed (#1507)."""

    @pytest.mark.issue(1507)
    def test_pkginfo_factory_registered_by_vcs_versioning(self) -> None:
        """Assert on the distribution metadata, not the merged EP view.

        In the monorepo venv setuptools-scm is installed too, so a plain
        ``entry_points(group=...)`` lookup cannot tell which package
        registered the factory -- which is exactly how #1507 escaped the
        test suite.
        """
        from importlib.metadata import distribution

        names = {
            ep.name
            for ep in distribution("vcs-versioning").entry_points
            if ep.group == "vcs_versioning.discover_workdir"
        }
        assert "pkginfo" in names

    @pytest.mark.issue(1507)
    def test_discovery_without_setuptools_scm(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Discovery finds PKG-INFO using only vcs-versioning's own factories."""
        from vcs_versioning import _compat, _worktree_discovery

        real = _compat.entry_points

        def core_only(*args: Any, **kwargs: Any) -> list[EntryPoint]:
            return [
                ep
                for ep in real(*args, **kwargs)
                if ep.value.startswith("vcs_versioning")
            ]

        monkeypatch.setattr(_worktree_discovery, "entry_points", core_only)

        (tmp_path / "PKG-INFO").write_text(
            "Metadata-Version: 2.1\nName: pkg\nVersion: 3.0.0\n",
            encoding="utf-8",
        )
        config = Configuration(relative_to=str(tmp_path / "pyproject.toml"))
        result = discover_workdir(config)
        assert isinstance(result, PkgInfoWorkdir)


class TestFallbackCandidatePriority:
    @pytest.mark.issue(1507)
    def test_metadata_outranks_pkginfo(self) -> None:
        """Richer metadata must win regardless of entry point order.

        A setuptools-scm built sdist carries both a root PKG-INFO and
        ``*.egg-info/scm_version.json``.  The two factories ship from
        different distributions, so entry point iteration order cannot
        decide this -- MetadataWorkdir knows distance, node and the
        tracked file list, PkgInfoWorkdir only a flat version.

        The egg-info factory itself lives in setuptools-scm, so the
        end to end check lives in its test suite (#1512); what core owns
        is the ranking the sort is driven by.
        """
        assert MetadataWorkdir.discovery_priority < PkgInfoWorkdir.discovery_priority

    @pytest.mark.issue(1507)
    def test_third_party_workdir_ranks_by_declared_priority(
        self, tmp_path: Path
    ) -> None:
        """discovery_priority is the knob, not entry point order."""

        class PoorWorkdir(FallbackWorkdir):
            def get_scm_version(self) -> ScmVersion | None:
                return meta("9.9.9", preformatted=True, config=self.config)

        class RichWorkdir(PoorWorkdir):
            discovery_priority = 5

        assert PoorWorkdir.discovery_priority == FallbackWorkdir.discovery_priority
        assert PoorWorkdir.discovery_priority > PkgInfoWorkdir.discovery_priority
        assert RichWorkdir.discovery_priority < MetadataWorkdir.discovery_priority
