"""Tests for setuptools-scm specific Configuration functionality.

Core Configuration tests have been moved to vcs-versioning/testing_vcs/test_config.py
"""

from __future__ import annotations

import textwrap

from pathlib import Path

import pytest

from setuptools_scm import Configuration


def test_config_from_pyproject(tmp_path: Path) -> None:
    fn = tmp_path / "pyproject.toml"
    fn.write_text(
        textwrap.dedent(
            """
            [tool.setuptools_scm]
            [project]
            description = "Factory ⸻ A code generator 🏭"
            authors = [{name = "Łukasz Langa"}]
            """
        ),
        encoding="utf-8",
    )
    Configuration.from_file(str(fn))


def test_config_from_file_protects_relative_to(tmp_path: Path) -> None:
    fn = tmp_path / "pyproject.toml"
    fn.write_text(
        textwrap.dedent(
            """
            [tool.setuptools_scm]
            relative_to = "dont_use_me"
            [project]
            description = "Factory ⸻ A code generator 🏭"
            authors = [{name = "Łukasz Langa"}]
            """
        ),
        encoding="utf-8",
    )
    with pytest.warns(
        UserWarning,
        match=".*pyproject.toml: at \\[tool.setuptools_scm\\]\n"
        "ignoring value relative_to='dont_use_me'"
        " as its always relative to the config file",
    ):
        Configuration.from_file(str(fn))


def test_config_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fn = tmp_path / "pyproject.toml"
    fn.write_text(
        textwrap.dedent(
            """
            [tool.setuptools_scm]
            root = "."
            [project]
            name = "teSt-.a"
            """
        ),
        encoding="utf-8",
    )
    pristine = Configuration.from_file(fn)
    monkeypatch.setenv(
        "SETUPTOOLS_SCM_OVERRIDES_FOR_TEST_A", '{root="..", fallback_root=".."}'
    )
    overridden = Configuration.from_file(fn)

    assert pristine.root != overridden.root
    assert pristine.fallback_root != overridden.fallback_root
