"""Tests for SCM metadata in egg-info and egg-info discovery.

Verifies that scm_version.json and scm_file_list.json can be written
to egg-info and discovered by the egg-info factory.
"""

from __future__ import annotations

from pathlib import Path

from vcs_versioning._config import Configuration
from vcs_versioning._fallback_workdir import MetadataWorkdir
from vcs_versioning._fallback_workdir import PkgInfoWorkdir
from vcs_versioning._scm_metadata import ScmVersionData
from vcs_versioning._scm_metadata import read_scm_file_list
from vcs_versioning._scm_metadata import read_scm_version_data
from vcs_versioning._scm_metadata import write_scm_file_list
from vcs_versioning._scm_metadata import write_scm_version_data


class TestEggInfoDiscovery:
    def test_discover_egg_info_metadata(self, tmp_path: Path) -> None:
        from setuptools_scm._integration._discover import discover_egg_info_metadata

        egg_info = tmp_path / "mypkg.egg-info"
        egg_info.mkdir()
        data = ScmVersionData(
            tag="1.0.0",
            distance=0,
            node="gabc1234",
            dirty=False,
            branch="main",
            node_date="2024-01-15",
        )
        write_scm_version_data(egg_info, data)
        write_scm_file_list(egg_info, ["src/__init__.py"])

        config = Configuration()
        result = discover_egg_info_metadata(tmp_path, config=config)
        assert result is not None
        assert isinstance(result, MetadataWorkdir)
        assert result.metadata_dir == egg_info

    def test_discover_egg_info_no_metadata(self, tmp_path: Path) -> None:
        from setuptools_scm._integration._discover import discover_egg_info_metadata

        egg_info = tmp_path / "mypkg.egg-info"
        egg_info.mkdir()
        # No scm_version.json -> should return None

        config = Configuration()
        result = discover_egg_info_metadata(tmp_path, config=config)
        assert result is None

    def test_discover_egg_info_empty_dir(self, tmp_path: Path) -> None:
        from setuptools_scm._integration._discover import discover_egg_info_metadata

        config = Configuration()
        result = discover_egg_info_metadata(tmp_path, config=config)
        assert result is None

    def test_metadata_workdir_reads_from_egg_info(self, tmp_path: Path) -> None:
        egg_info = tmp_path / "mypkg.egg-info"
        egg_info.mkdir()
        data = ScmVersionData(
            tag="2.5.1",
            distance=7,
            node="gdef5678",
            dirty=True,
            branch="develop",
            node_date="2024-03-20",
        )
        write_scm_version_data(egg_info, data)
        write_scm_file_list(egg_info, ["mypkg/__init__.py", "mypkg/core.py"])

        config = Configuration()
        wd = MetadataWorkdir(path=tmp_path, metadata_dir=egg_info, _config=config)

        version = wd.get_scm_version()
        assert version is not None
        assert str(version.tag) == "2.5.1"
        assert version.distance == 7
        assert version.dirty is True

        files = wd.list_tracked_files()
        assert files == ["mypkg/__init__.py", "mypkg/core.py"]


class TestDiscoverPkgInfo:
    def test_discover_pkginfo(self, tmp_path: Path) -> None:
        from setuptools_scm._integration._discover import discover_pkginfo

        (tmp_path / "PKG-INFO").write_text("Version: 1.0\n", encoding="utf-8")
        config = Configuration()
        result = discover_pkginfo(tmp_path, config=config)
        assert result is not None
        assert isinstance(result, PkgInfoWorkdir)

    def test_discover_pkginfo_none(self, tmp_path: Path) -> None:
        from setuptools_scm._integration._discover import discover_pkginfo

        config = Configuration()
        assert discover_pkginfo(tmp_path, config=config) is None


class TestScmMetadataRoundTrip:
    def test_write_and_read_version_data(self, tmp_path: Path) -> None:
        data = ScmVersionData(
            tag="3.0.0rc1",
            distance=0,
            node=None,
            dirty=False,
            branch=None,
            node_date=None,
        )
        write_scm_version_data(tmp_path, data)
        result = read_scm_version_data(tmp_path)
        assert result is not None
        assert result.tag == "3.0.0rc1"
        assert result.distance == 0
        assert result.node is None

    def test_write_and_read_file_list(self, tmp_path: Path) -> None:
        files = ["a.py", "b/c.py", "d/e/f.py"]
        write_scm_file_list(tmp_path, files)
        result = read_scm_file_list(tmp_path)
        assert result == files
