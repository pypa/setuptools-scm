"""Tests for per-project overrides from .config/python-vcs-versioning.toml."""

from __future__ import annotations

from pathlib import Path

from vcs_versioning._project_overrides import read_project_overrides


class TestReadProjectOverrides:
    def test_no_config_file(self, tmp_path: Path) -> None:
        result = read_project_overrides(tmp_path, "sub/project")
        assert result == {}

    def test_empty_config(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".config"
        config_dir.mkdir()
        (config_dir / "python-vcs-versioning.toml").write_text("", encoding="utf-8")
        result = read_project_overrides(tmp_path, "sub/project")
        assert result == {}

    def test_matching_project_path(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".config"
        config_dir.mkdir()
        (config_dir / "python-vcs-versioning.toml").write_text(
            '["sub/project"]\nversion_scheme = "calver-by-date"\ntag_regex = "mymod-v*"\n',
            encoding="utf-8",
        )
        result = read_project_overrides(tmp_path, "sub/project")
        assert result == {
            "version_scheme": "calver-by-date",
            "tag_regex": "mymod-v*",
        }

    def test_non_matching_project_path(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".config"
        config_dir.mkdir()
        (config_dir / "python-vcs-versioning.toml").write_text(
            '["other/project"]\nversion_scheme = "no-guess-dev"\n',
            encoding="utf-8",
        )
        result = read_project_overrides(tmp_path, "sub/project")
        assert result == {}

    def test_top_level_project_uses_dot(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".config"
        config_dir.mkdir()
        (config_dir / "python-vcs-versioning.toml").write_text(
            '["."]\nversion_scheme = "post-release"\n',
            encoding="utf-8",
        )
        result = read_project_overrides(tmp_path, "")
        assert result == {"version_scheme": "post-release"}

    def test_invalid_toml_returns_empty(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".config"
        config_dir.mkdir()
        (config_dir / "python-vcs-versioning.toml").write_text(
            "this is not valid toml {{{{",
            encoding="utf-8",
        )
        result = read_project_overrides(tmp_path, "sub/project")
        assert result == {}
