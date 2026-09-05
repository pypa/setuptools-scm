"""Tests for the setuptools.file_finders entry point deprecation."""

from __future__ import annotations

import warnings

from pathlib import Path
from textwrap import dedent

import pytest

from vcs_versioning._file_finders import find_files

_FILE_FINDERS_DEPRECATION = "setuptools.file_finders"


def _file_finder_deprecations(
    caught: list[warnings.WarningMessage],
) -> list[warnings.WarningMessage]:
    return [
        w
        for w in caught
        if issubclass(w.category, DeprecationWarning)
        and _FILE_FINDERS_DEPRECATION in str(w.message)
    ]


@pytest.mark.issue(1407)
def test_find_files_warns_when_unconfigured(tmp_path: Path) -> None:
    """A project without setuptools-scm config must warn on the entry point."""
    (tmp_path / "pyproject.toml").write_text(
        dedent("""\
            [build-system]
            requires = ["setuptools>=61", "setuptools-scm"]
            build-backend = "setuptools.build_meta"

            [project]
            name = "unconfigured"
            version = "1.0.0"
        """),
        encoding="utf-8",
    )
    with pytest.warns(DeprecationWarning, match=_FILE_FINDERS_DEPRECATION):
        find_files(str(tmp_path))


@pytest.mark.issue(1407)
def test_find_files_no_warn_when_configured(tmp_path: Path) -> None:
    """An explicit [tool.setuptools_scm] section silences the deprecation."""
    (tmp_path / "pyproject.toml").write_text(
        "[tool.setuptools_scm]\n",
        encoding="utf-8",
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        find_files(str(tmp_path))
    assert _file_finder_deprecations(caught) == []


@pytest.mark.issue(1407)
def test_find_files_no_warn_when_setup_py_configures(tmp_path: Path) -> None:
    """setup.py use_scm_version counts as configuration."""
    (tmp_path / "setup.py").write_text(
        "from setuptools import setup\nsetup(use_scm_version=True)\n",
        encoding="utf-8",
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        find_files(str(tmp_path))
    assert _file_finder_deprecations(caught) == []


@pytest.mark.issue(1407)
def test_find_files_no_warn_when_simple_extra(tmp_path: Path) -> None:
    """setuptools-scm[simple] with a dynamic version counts as configuration."""
    (tmp_path / "pyproject.toml").write_text(
        dedent("""\
            [build-system]
            requires = ["setuptools>=61", "setuptools-scm[simple]"]
            build-backend = "setuptools.build_meta"

            [project]
            name = "simple-pkg"
            dynamic = ["version"]
        """),
        encoding="utf-8",
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        find_files(str(tmp_path))
    assert _file_finder_deprecations(caught) == []
