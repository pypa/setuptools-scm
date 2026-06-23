"""Tests for _legacy_parse.py — legacy EP dispatch and config.parse workdir."""

from __future__ import annotations

import warnings
from pathlib import Path
from unittest.mock import patch

import pytest
from vcs_versioning import _types as _t
from vcs_versioning._config import Configuration
from vcs_versioning._legacy_parse import (
    LegacyParseWorkdir,
    has_legacy_parse_eps,
    parse_fallback_version,
    parse_scm_version,
    resolved_fallback_root,
)
from vcs_versioning._scm_version import ScmVersion
from vcs_versioning._version_cls import Version

# ---------------------------------------------------------------------------
# LegacyParseWorkdir
# ---------------------------------------------------------------------------


class TestLegacyParseWorkdir:
    def _make_config(self, tmp_path: Path) -> Configuration:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "[project]\nname='test-pkg'\n[tool.vcs-versioning]\n",
            encoding="utf-8",
        )
        return Configuration.from_file(pyproject)

    def test_requires_parse_fn(self, tmp_path: Path) -> None:
        with pytest.raises(TypeError, match="parse_fn"):
            LegacyParseWorkdir(path=tmp_path)  # type: ignore[call-arg]

    def test_get_scm_version_emits_deprecation(self, tmp_path: Path) -> None:
        config = self._make_config(tmp_path)

        def fake_parse(root: _t.PathT, *, config: Configuration) -> ScmVersion | None:
            return ScmVersion(tag=Version("1.0.0"), config=config)

        wd = LegacyParseWorkdir(path=tmp_path, parse_fn=fake_parse)
        wd._config = config

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = wd.get_scm_version()

        assert result is not None
        assert str(result.tag) == "1.0.0"
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "config.parse is deprecated" in str(w[0].message)

    def test_get_scm_version_returns_none_from_parse(self, tmp_path: Path) -> None:
        config = self._make_config(tmp_path)

        def fake_parse(root: _t.PathT, *, config: Configuration) -> ScmVersion | None:
            return None

        wd = LegacyParseWorkdir(path=tmp_path, parse_fn=fake_parse)
        wd._config = config

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            assert wd.get_scm_version() is None

    def test_get_scm_version_rejects_non_scm_version(self, tmp_path: Path) -> None:
        config = self._make_config(tmp_path)

        def bad_parse(root: _t.PathT, *, config: Configuration) -> ScmVersion | None:
            return "not-a-version"  # type: ignore[return-value]

        wd = LegacyParseWorkdir(path=tmp_path, parse_fn=bad_parse)
        wd._config = config

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            with pytest.raises(TypeError, match="please return a parsed version"):
                wd.get_scm_version()


# ---------------------------------------------------------------------------
# resolved_fallback_root
# ---------------------------------------------------------------------------


class TestResolvedFallbackRoot:
    def test_absolute_fallback_root(self, tmp_path: Path) -> None:
        config = Configuration(
            relative_to=str(tmp_path / "pyproject.toml"),
            root=".",
            fallback_root=str(tmp_path / "sub"),
        )
        assert resolved_fallback_root(config) == str((tmp_path / "sub").resolve())

    def test_relative_fallback_root(self, tmp_path: Path) -> None:
        config = Configuration(
            relative_to=str(tmp_path / "pyproject.toml"),
            root=".",
            fallback_root="..",
        )
        result = resolved_fallback_root(config)
        assert Path(result).is_absolute()
        assert result == str((tmp_path / "..").resolve())


# ---------------------------------------------------------------------------
# parse_scm_version / parse_fallback_version
# ---------------------------------------------------------------------------


class TestParseDispatch:
    def test_parse_scm_version_no_eps(self, tmp_path: Path) -> None:
        """With no third-party EPs, returns None."""
        config = Configuration(
            relative_to=str(tmp_path / "pyproject.toml"),
            root=".",
        )
        with patch(
            "vcs_versioning._entrypoints.version_from_entrypoint", return_value=None
        ):
            assert parse_scm_version(config) is None

    def test_parse_fallback_version_no_eps(self, tmp_path: Path) -> None:
        """With no third-party EPs, returns None."""
        config = Configuration(
            relative_to=str(tmp_path / "pyproject.toml"),
            root=".",
        )
        with patch(
            "vcs_versioning._entrypoints.version_from_entrypoint", return_value=None
        ):
            assert parse_fallback_version(config) is None


# ---------------------------------------------------------------------------
# has_legacy_parse_eps
# ---------------------------------------------------------------------------


class TestHasLegacyParseEps:
    def test_returns_false_with_only_builtin_eps(self) -> None:
        assert has_legacy_parse_eps() is False
