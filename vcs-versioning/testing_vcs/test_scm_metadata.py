"""Tests for scm_version.json + scm_file_list.json read/write round-trip."""

from __future__ import annotations

from pathlib import Path

import pytest
from vcs_versioning._scm_metadata import (
    ScmVersionData,
    read_scm_file_list,
    read_scm_version_data,
    scm_version_data_from_scm_version,
    write_scm_file_list,
    write_scm_version_data,
)


class TestScmVersionDataRoundTrip:
    @pytest.fixture()
    def sample_data(self) -> ScmVersionData:
        return ScmVersionData(
            tag="1.2.3",
            distance=5,
            node="abc1234",
            dirty=False,
            branch="main",
            node_date="2024-01-15",
        )

    def test_write_then_read(self, tmp_path: Path, sample_data: ScmVersionData) -> None:
        write_scm_version_data(tmp_path, sample_data)
        result = read_scm_version_data(tmp_path)
        assert result is not None
        assert result.tag == "1.2.3"
        assert result.distance == 5
        assert result.node == "abc1234"
        assert result.dirty is False
        assert result.branch == "main"
        assert result.node_date == "2024-01-15"

    def test_read_missing_returns_none(self, tmp_path: Path) -> None:
        assert read_scm_version_data(tmp_path) is None

    def test_read_corrupted_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / "scm_version.json").write_text("not valid json", encoding="utf-8")
        assert read_scm_version_data(tmp_path) is None

    def test_read_incomplete_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / "scm_version.json").write_text('{"tag": "1.0"}', encoding="utf-8")
        # Missing required fields like "distance"
        assert read_scm_version_data(tmp_path) is None

    def test_dirty_flag(self, tmp_path: Path) -> None:
        data = ScmVersionData(
            tag="0.1.0",
            distance=0,
            node=None,
            dirty=True,
            branch=None,
            node_date=None,
        )
        write_scm_version_data(tmp_path, data)
        result = read_scm_version_data(tmp_path)
        assert result is not None
        assert result.dirty is True
        assert result.node is None
        assert result.branch is None
        assert result.node_date is None

    def test_to_dict(self, sample_data: ScmVersionData) -> None:
        d = sample_data.to_dict()
        assert d == {
            "tag": "1.2.3",
            "distance": 5,
            "node": "abc1234",
            "dirty": False,
            "branch": "main",
            "node_date": "2024-01-15",
        }

    def test_creates_directory(
        self, tmp_path: Path, sample_data: ScmVersionData
    ) -> None:
        nested = tmp_path / "a" / "b" / "c"
        write_scm_version_data(nested, sample_data)
        assert (nested / "scm_version.json").is_file()


class TestScmFileListRoundTrip:
    def test_write_then_read(self, tmp_path: Path) -> None:
        files = [
            "src/mypackage/__init__.py",
            "src/mypackage/core.py",
            "pyproject.toml",
        ]
        write_scm_file_list(tmp_path, files)
        result = read_scm_file_list(tmp_path)
        assert result == files

    def test_empty_list(self, tmp_path: Path) -> None:
        write_scm_file_list(tmp_path, [])
        result = read_scm_file_list(tmp_path)
        assert result == []

    def test_read_missing_returns_none(self, tmp_path: Path) -> None:
        assert read_scm_file_list(tmp_path) is None

    def test_read_corrupted_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / "scm_file_list.json").write_text("{broken", encoding="utf-8")
        assert read_scm_file_list(tmp_path) is None


class TestScmVersionDataFromScmVersion:
    def test_conversion_from_live_scm_version(self) -> None:
        from datetime import date

        from vcs_versioning._config import Configuration
        from vcs_versioning._scm_version import meta

        config = Configuration()
        sv = meta(
            tag="1.0.0",
            distance=3,
            node="gabc1234",
            dirty=True,
            branch="feature",
            config=config,
            node_date=date(2024, 6, 15),
        )
        data = scm_version_data_from_scm_version(sv)
        assert data.tag == "1.0.0"
        assert data.distance == 3
        assert data.node == "gabc1234"
        assert data.dirty is True
        assert data.branch == "feature"
        assert data.node_date == "2024-06-15"

    def test_none_node_date(self) -> None:
        from vcs_versioning._config import Configuration
        from vcs_versioning._scm_version import meta

        config = Configuration()
        sv = meta(tag="2.0.0", config=config)
        data = scm_version_data_from_scm_version(sv)
        assert data.node_date is None
