"""Tests for TagConfiguration (tag.prefix and tag.strict)."""

from __future__ import annotations

import warnings

import pytest
from packaging.version import Version
from vcs_versioning import Configuration
from vcs_versioning._config import TagConfiguration
from vcs_versioning._scm_version import tag_to_version


class TestTagConfiguration:
    def test_default_values(self) -> None:
        tc = TagConfiguration()
        assert tc.prefix == ""
        assert tc.strict is None

    def test_from_data_none(self) -> None:
        tc = TagConfiguration.from_data(None)
        assert tc.prefix == ""
        assert tc.strict is None

    def test_from_data_prefix(self) -> None:
        tc = TagConfiguration.from_data({"prefix": "hatchling-v"})
        assert tc.prefix == "hatchling-v"
        assert tc.strict is None

    def test_from_data_strict(self) -> None:
        tc = TagConfiguration.from_data({"strict": True})
        assert tc.strict is True

    def test_from_data_both(self) -> None:
        tc = TagConfiguration.from_data({"prefix": "pkg-", "strict": True})
        assert tc.prefix == "pkg-"
        assert tc.strict is True


class TestDescribeMatchGlob:
    def test_permissive_no_prefix(self) -> None:
        tc = TagConfiguration(prefix="", strict=False)
        assert tc.describe_match_glob() == "*[0-9]*"

    def test_strict_no_prefix(self) -> None:
        tc = TagConfiguration(prefix="", strict=True)
        assert tc.describe_match_glob() == "*[0-9]*.*[0-9]*"

    def test_permissive_with_prefix(self) -> None:
        tc = TagConfiguration(prefix="hatchling-v", strict=False)
        assert tc.describe_match_glob() == "hatchling-v*[0-9]*"

    def test_strict_with_prefix(self) -> None:
        tc = TagConfiguration(prefix="pkg-", strict=True)
        assert tc.describe_match_glob() == "pkg-*[0-9]*.*[0-9]*"

    def test_none_strict_uses_permissive_glob(self) -> None:
        tc = TagConfiguration(prefix="", strict=None)
        assert tc.describe_match_glob() == "*[0-9]*"


class TestTagStrictWarning:
    def test_none_strict_no_warning(self) -> None:
        """tag.strict=None no longer warns (suppressed per #1422, see #1429)."""
        with warnings.catch_warnings():
            warnings.simplefilter("error", FutureWarning)
            Configuration(tag=TagConfiguration(strict=None))

    def test_true_strict_no_warning(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error", FutureWarning)
            Configuration(tag=TagConfiguration(strict=True))

    def test_false_strict_no_warning(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error", FutureWarning)
            Configuration(tag=TagConfiguration(strict=False))


class TestTagPrefixStripping:
    """Test that tag.prefix is stripped before tag_regex matching."""

    def test_prefix_stripped_from_tag(self) -> None:
        config = Configuration(tag=TagConfiguration(prefix="hatchling-v"))
        version = tag_to_version("hatchling-v1.0.0", config)
        assert version is not None
        assert str(version) == "1.0.0"

    def test_no_prefix_no_stripping(self) -> None:
        config = Configuration(tag=TagConfiguration(prefix=""))
        version = tag_to_version("v1.0.0", config)
        assert version is not None
        assert str(version) == "1.0.0"

    def test_wrong_prefix_not_stripped(self) -> None:
        """When prefix doesn't match, the full tag is passed to tag_regex.

        The default tag_regex still handles dashed prefixes, so the tag
        may still parse -- but the prefix is NOT stripped, meaning
        git describe --match would have already filtered it out in practice.
        """
        config = Configuration(tag=TagConfiguration(prefix="other-"))
        version = tag_to_version("hatchling-v1.0.0", config)
        # Default tag_regex matches and extracts "v1.0.0" from dashed prefix
        assert version is not None

    def test_prefix_v_strips_v(self) -> None:
        config = Configuration(tag=TagConfiguration(prefix="v"))
        version = tag_to_version("v1.2.3", config)
        assert version is not None
        assert str(version) == "1.2.3"


class TestTagToVersionSuffixPreservation:
    """Test that tag_to_version preserves +local suffixes when possible."""

    def test_tag_with_build_metadata_preserved(self) -> None:
        config = Configuration()
        version = tag_to_version("1.2.3+build.123", config)
        assert version is not None
        assert str(version) == "1.2.3+build.123"

    def test_tag_with_invalid_suffix_stripped(self) -> None:
        config = Configuration()
        # "+invalid!!" is captured as suffix by the default regex but
        # Version("1.2.3+invalid!!") raises, so the suffix gets stripped
        with pytest.warns(UserWarning, match="will be stripped of its suffix"):
            version = tag_to_version("1.2.3+invalid!!", config)
        assert version is not None
        assert str(version) == "1.2.3"

    @pytest.mark.parametrize(
        ("tag", "expected"),
        [
            ("1.0.0+ci.456", "1.0.0+ci.456"),
            ("v2.0.0+build.789", "2.0.0+build.789"),
            ("release-1.0.0+metadata", "1.0.0+metadata"),
        ],
    )
    def test_various_build_metadata_tags(self, tag: str, expected: str) -> None:
        config = Configuration()
        version = tag_to_version(tag, config)
        assert version is not None
        assert str(version) == expected

    def test_custom_version_cls_parse_failure_returns_none(self) -> None:
        """When version_cls rejects the base version string, return None."""

        def rejecting_version_cls(version_str: str) -> Version:
            raise ValueError(f"rejected: {version_str}")

        config = Configuration(version_cls=rejecting_version_cls)  # type: ignore[arg-type]
        with pytest.warns(UserWarning, match="could not be parsed"):
            result = tag_to_version("1.2.3", config)
        assert result is None


class TestConfigFromData:
    """Test that Configuration.from_data correctly parses tag config."""

    def test_tag_in_from_data(self) -> None:
        config = Configuration.from_data(
            relative_to=".",
            data={
                "dist_name": "test",
                "tag": {"prefix": "mylib-", "strict": True},
            },
        )
        assert config.tag.prefix == "mylib-"
        assert config.tag.strict is True

    def test_no_tag_in_from_data(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error", FutureWarning)
            config = Configuration.from_data(
                relative_to=".",
                data={"dist_name": "test"},
            )
        assert config.tag.prefix == ""
        assert config.tag.strict is None


class TestDescribeCommandConflictWarning:
    def test_no_warning_when_prefix_and_describe_command_both_set(self) -> None:
        """Suppressed per #1422, see #1429 for follow-up."""
        from vcs_versioning._config import GitConfiguration, ScmConfiguration

        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            Configuration(
                tag=TagConfiguration(prefix="v", strict=True),
                scm=ScmConfiguration(
                    git=GitConfiguration(describe_command=["git", "describe", "--tags"])
                ),
            )
