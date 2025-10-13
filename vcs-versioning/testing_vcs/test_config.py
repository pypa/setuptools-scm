"""Tests for core Configuration functionality."""

from __future__ import annotations

import re

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


def test_config_regex_init() -> None:
    tag_regex = re.compile(r"v(\d+)")
    conf = Configuration(tag_regex=tag_regex)
    assert conf.tag_regex is tag_regex


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
