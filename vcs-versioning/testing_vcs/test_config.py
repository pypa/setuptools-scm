"""Tests for core Configuration functionality."""

from __future__ import annotations

import re
import warnings

import pytest
from vcs_versioning import Configuration
from vcs_versioning._config import DEFAULT_TAG_REGEX, TagConfiguration


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
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        config = Configuration()
    match = config.tag.regex.match(tag)
    assert match
    version = match.group("version")
    assert version == expected_version


def test_config_regex_init_via_tag() -> None:
    tag_regex = re.compile(r"v(\d+)")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        conf = Configuration(tag=TagConfiguration(regex=tag_regex))
    assert conf.tag.regex is tag_regex


def test_deprecated_tag_regex_accessor() -> None:
    """Accessing config.tag_regex proxies to config.tag.regex with a warning."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        config = Configuration()
    with pytest.warns(DeprecationWarning, match="Use 'tag.regex' instead"):
        regex = config.tag_regex  # type: ignore[attr-defined]
    assert regex.pattern == config.tag.regex.pattern


def test_deprecated_tag_regex_init_var() -> None:
    """Passing tag_regex= to Configuration emits DeprecationWarning."""
    tag_regex = re.compile(r"v(\d+)")
    with pytest.warns(DeprecationWarning, match="Use 'tag.regex' instead"):
        conf = Configuration(tag_regex=tag_regex)
    assert conf.tag.regex is tag_regex


@pytest.mark.issue(1434)
def test_omitting_tag_regex_no_deprecation_warning() -> None:
    """Omitting tag_regex (None default) should not emit DeprecationWarning."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        Configuration()


@pytest.mark.issue(1434)
def test_explicit_default_tag_regex_warns() -> None:
    """Explicitly passing DEFAULT_TAG_REGEX still warns (deprecated param)."""
    with pytest.warns(DeprecationWarning, match="Use 'tag.regex' instead"):
        Configuration(tag_regex=DEFAULT_TAG_REGEX)


def test_tag_regex_conflict() -> None:
    """Cannot set both tag_regex= and tag.regex simultaneously."""
    with pytest.raises(
        ValueError,
        match="Cannot specify both 'tag_regex'.*and.*'tag.regex'",
    ):
        Configuration(
            tag_regex=re.compile(r"v(\d+)"),
            tag=TagConfiguration(regex=re.compile(r"V(\d+)")),
        )


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
        Configuration(tag=TagConfiguration(regex=re.compile(tag_regex)))
