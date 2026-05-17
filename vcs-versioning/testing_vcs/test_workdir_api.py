"""Tests for ScmWorkdir and FallbackWorkdir method APIs."""

from __future__ import annotations

from pathlib import Path

import pytest
from vcs_versioning._backends._scm_workdir import ScmWorkdir, Workdir
from vcs_versioning._fallback_workdir import (
    FallbackWorkdir,
    PkgInfoWorkdir,
    StaticWorkdir,
)


class TestScmWorkdir:
    def test_workdir_alias_is_scm_workdir(self) -> None:
        assert Workdir is ScmWorkdir

    def test_path_only_defaults_project_root(self, tmp_path: Path) -> None:
        wd = ScmWorkdir(path=tmp_path)
        assert wd.project_root == tmp_path
        assert wd.project_path == ""

    def test_project_root_same_as_path(self, tmp_path: Path) -> None:
        wd = ScmWorkdir(path=tmp_path, project_root=tmp_path)
        assert wd.project_path == ""

    def test_project_root_nested(self, tmp_path: Path) -> None:
        project = tmp_path / "python" / "modules" / "mymod"
        project.mkdir(parents=True)
        wd = ScmWorkdir(path=tmp_path, project_root=project)
        assert wd.project_path == "python/modules/mymod"

    def test_run_describe_not_implemented(self, tmp_path: Path) -> None:
        from vcs_versioning._config import Configuration

        wd = ScmWorkdir(path=tmp_path, _config=Configuration())
        with pytest.raises(NotImplementedError):
            wd.run_describe()

    def test_get_scm_version_not_implemented(self, tmp_path: Path) -> None:
        from vcs_versioning._config import Configuration

        wd = ScmWorkdir(path=tmp_path, _config=Configuration())
        with pytest.raises(NotImplementedError):
            wd.get_scm_version()

    def test_list_tracked_files_not_implemented(self, tmp_path: Path) -> None:
        wd = ScmWorkdir(path=tmp_path)
        with pytest.raises(NotImplementedError):
            wd.list_tracked_files()

    def test_is_file_tracked_not_implemented(self, tmp_path: Path) -> None:
        wd = ScmWorkdir(path=tmp_path)
        with pytest.raises(NotImplementedError):
            wd.is_file_tracked(tmp_path / "foo.py")


class TestFallbackWorkdir:
    def test_get_scm_version_not_implemented(self, tmp_path: Path) -> None:
        from vcs_versioning._config import Configuration

        wd = FallbackWorkdir(path=tmp_path, _config=Configuration())
        with pytest.raises(NotImplementedError):
            wd.get_scm_version()

    def test_list_tracked_files_not_implemented(self, tmp_path: Path) -> None:
        wd = FallbackWorkdir(path=tmp_path)
        with pytest.raises(NotImplementedError):
            wd.list_tracked_files()


class TestStaticWorkdir:
    def test_fallback_version(self, tmp_path: Path) -> None:
        from vcs_versioning._config import Configuration

        config = Configuration(fallback_version="1.2.3")
        wd = StaticWorkdir(path=tmp_path, _config=config)
        version = wd.get_scm_version()
        assert version is not None
        assert str(version.tag) == "1.2.3"
        assert version.preformatted is True

    def test_no_fallback(self, tmp_path: Path) -> None:
        from vcs_versioning._config import Configuration

        config = Configuration()
        wd = StaticWorkdir(path=tmp_path, _config=config)
        assert wd.get_scm_version() is None

    def test_empty_file_list(self, tmp_path: Path) -> None:
        wd = StaticWorkdir(path=tmp_path)
        assert wd.list_tracked_files() == []

    def test_parentdir_prefix(self, tmp_path: Path) -> None:
        from vcs_versioning._config import Configuration

        project_dir = tmp_path / "mypackage-1.0.0"
        project_dir.mkdir()
        config = Configuration(parentdir_prefix_version="mypackage-")
        wd = StaticWorkdir(path=project_dir, _config=config)
        version = wd.get_scm_version()
        assert version is not None
        assert str(version.tag) == "1.0.0"


class TestPkgInfoWorkdir:
    def test_reads_version_from_pkginfo(self, tmp_path: Path) -> None:
        from vcs_versioning._config import Configuration

        config = Configuration()
        pkginfo = tmp_path / "PKG-INFO"
        pkginfo.write_text(
            "Metadata-Version: 2.1\nName: mypackage\nVersion: 2.3.4\n",
            encoding="utf-8",
        )
        wd = PkgInfoWorkdir(path=tmp_path, _config=config)
        version = wd.get_scm_version()
        assert version is not None
        assert str(version.tag) == "2.3.4"
        assert version.preformatted is True

    def test_returns_none_for_unknown_version(self, tmp_path: Path) -> None:
        from vcs_versioning._config import Configuration

        config = Configuration()
        pkginfo = tmp_path / "PKG-INFO"
        pkginfo.write_text(
            "Metadata-Version: 2.1\nName: mypackage\nVersion: UNKNOWN\n",
            encoding="utf-8",
        )
        wd = PkgInfoWorkdir(path=tmp_path, _config=config)
        assert wd.get_scm_version() is None

    def test_returns_none_when_missing(self, tmp_path: Path) -> None:
        from vcs_versioning._config import Configuration

        config = Configuration()
        wd = PkgInfoWorkdir(path=tmp_path, _config=config)
        assert wd.get_scm_version() is None
