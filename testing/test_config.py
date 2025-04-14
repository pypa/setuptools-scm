from __future__ import annotations

import re
import textwrap

from pathlib import Path

import pytest

from setuptools_scm import Configuration


@pytest.mark.parametrize(
    ("tag", "expected_version"),
    [
        ("apache-arrow-0.9.0", "0.9.0"),
        ("arrow-0.9.0", "0.9.0"),
        ("arrow-0.9.0-rc", "0.9.0-rc"),
        ("arrow-1", "1"),
        ("arrow-1+", "1"),
        ("arrow-1+foo", "1"),
        ("arrow-1.1+foo", "1.1"),
        ("v1.1", "v1.1"),
        ("V1.1", "V1.1"),
    ],
)
def test_tag_regex(tag: str, expected_version: str) -> None:
    config = Configuration()
    match = config.tag_regex.match(tag)
    assert match
    version = match.group("version")
    assert version == expected_version


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
    assert Configuration.from_file(str(fn))


def test_config_regex_init() -> None:
    tag_regex = re.compile(r"v(\d+)")
    conf = Configuration(tag_regex=tag_regex)
    assert conf.tag_regex is tag_regex


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
        assert Configuration.from_file(str(fn))


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


@pytest.mark.parametrize(
    "tag_regex",
    [
        r".*",
        r"(.+)(.+)",
        r"((.*))",
    ],
)
def test_config_bad_regex(tag_regex: str) -> None:
    with pytest.raises(
        ValueError,
        match=(
            f"Expected tag_regex '{re.escape(tag_regex)}' to contain a single match"
            " group or a group named 'version' to identify the version part of any"
            " tag."
        ),
    ):
        Configuration(tag_regex=re.compile(tag_regex))
