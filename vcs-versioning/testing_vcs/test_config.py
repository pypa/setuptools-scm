"""Tests for core Configuration functionality."""

from __future__ import annotations

import re
import warnings
from pathlib import Path
from typing import Any, cast

import pytest
from vcs_versioning import Configuration
from vcs_versioning._config import DEFAULT_TAG_REGEX, TagConfiguration
from vcs_versioning._get_version_impl import get_version


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


#: Patterns that ``re`` cannot compile at all.  Unlike the patterns in
#: ``test_config_bad_regex`` (which compile but do not carry a single version
#: group), these used to fail inside ``re`` itself.
UNCOMPILABLE_TAG_REGEXES = ["[vV", "(unclosed", "a{2,1}", "*", "\\"]


def _tag_config_with_pattern_string(regex: str) -> TagConfiguration:
    """Build a ``TagConfiguration`` from raw pattern text.

    The dataclass field is annotated ``Pattern[str]`` because callers are
    expected to hand in a compiled pattern, but the runtime accepts source
    text too (``TagConfiguration.from_data`` passes exactly that through), so
    the raw string is what the validation has to be driven with here.
    """
    return TagConfiguration(regex=cast(Any, regex))


@pytest.mark.parametrize("tag_regex", UNCOMPILABLE_TAG_REGEXES)
def test_uncompilable_tag_regex_reports_value_error(tag_regex: str) -> None:
    """A tag regex that ``re`` rejects names the option it came from.

    ``re.error`` is not a ``ValueError`` and is raised from ``re._parser``, so
    the traceback never mentions ``tag_regex``/``tag.regex`` -- unlike every
    other bad setting, which the house style reports as a ``ValueError`` with
    the offending value and what was expected of it.
    """
    with pytest.raises(ValueError, match="to be a valid regular expression") as info:
        _tag_config_with_pattern_string(tag_regex)
    message = str(info.value)
    assert repr(tag_regex) in message
    assert "tag_regex" in message
    assert not isinstance(info.value, re.error)


@pytest.mark.parametrize("tag_regex", UNCOMPILABLE_TAG_REGEXES)
def test_uncompilable_tag_regex_reports_value_error_from_data(
    tag_regex: str,
) -> None:
    """The same holds for the ``tag.regex`` spelling in pyproject data."""
    with pytest.raises(ValueError, match="to be a valid regular expression"):
        TagConfiguration.from_data({"regex": tag_regex})


def test_uncompilable_tag_regex_from_configuration_data() -> None:
    with pytest.raises(ValueError, match="to be a valid regular expression"):
        Configuration.from_data(relative_to=".", data={"tag": {"regex": "[vV"}})


def test_uncompilable_deprecated_tag_regex_from_configuration_data() -> None:
    with pytest.warns(DeprecationWarning, match="tag_regex"):
        with pytest.raises(ValueError, match="to be a valid regular expression"):
            Configuration.from_data(relative_to=".", data={"tag_regex": "[vV"})


def test_uncompilable_tag_regex_in_pyproject(tmp_path: Path) -> None:
    """The pyproject spelling reports the option instead of a ``re`` traceback."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.setuptools_scm]\ntag_regex = "[vV"\n')
    with pytest.warns(DeprecationWarning, match="tag_regex"):
        with pytest.raises(ValueError, match="to be a valid regular expression"):
            Configuration.from_file(pyproject)


def test_uncompilable_get_version_tag_regex_parameter(tmp_path: Path) -> None:
    """``get_version(tag_regex=...)`` fails the same way as the config paths."""
    with pytest.warns(DeprecationWarning, match="tag_regex"):
        with pytest.raises(ValueError, match="to be a valid regular expression"):
            get_version(
                root=str(tmp_path),
                tag_regex="[vV",
                fallback_version="1.0.0",
            )
