"""Tests for ``tag.strict`` on the Mercurial backend.

Covers both the behaviour (strict must apply to the tags on the current
changeset, not just to the distance path) and the divergence diagnostic --
see #1495, follow-up to #1429.
"""

from __future__ import annotations

import logging

import pytest
from vcs_versioning import Configuration
from vcs_versioning._backends._hg import hg_tag_pattern, matches_tag_pattern
from vcs_versioning._config import TagConfiguration
from vcs_versioning._get_version_impl import _get_version
from vcs_versioning.test_api import WorkDir


@pytest.fixture
def wd(wd: WorkDir) -> WorkDir:
    return wd.setup_hg()


def version_for(wd: WorkDir, strict: bool | None) -> str:
    config = Configuration(
        root=wd.cwd, fallback_root=wd.cwd, tag=TagConfiguration(strict=strict)
    )
    version = _get_version(config, force_write_version_files=False)
    assert version is not None
    return version


def reported(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


class TestTagPattern:
    """The regex handed to ``latesttag()`` and used to filter head tags."""

    def test_permissive_pattern(self) -> None:
        config = Configuration(tag=TagConfiguration(strict=False))
        assert hg_tag_pattern(config) == r"\d+"

    def test_strict_pattern(self) -> None:
        config = Configuration(tag=TagConfiguration(strict=True))
        assert hg_tag_pattern(config) == r"\d+\.\d+"

    def test_prefix_is_escaped(self) -> None:
        config = Configuration(tag=TagConfiguration(prefix="pkg.v", strict=True))
        assert hg_tag_pattern(config) == r"pkg\.v\d+\.\d+"

    def test_strict_override_ignores_config(self) -> None:
        """The diagnostics ask what the *other* setting would have matched."""
        config = Configuration(tag=TagConfiguration(strict=None))
        assert hg_tag_pattern(config, strict=True) == r"\d+\.\d+"

    @pytest.mark.parametrize(
        ("tag", "matches"),
        [
            ("v1.2.3", True),
            ("1.0", True),
            ("2024", False),
            ("event-2024", False),
            ("nightly", False),
        ],
    )
    def test_strict_membership(self, tag: str, matches: bool) -> None:
        config = Configuration(tag=TagConfiguration(strict=None))
        result = matches_tag_pattern(tag, config, strict=True)
        assert result is matches


class TestStrictOnTaggedChangeset:
    """#1495: tag.strict was ignored when the changeset itself carries tags."""

    def test_event_tag_on_head_is_rejected_when_strict(self, wd: WorkDir) -> None:
        """Strict must fall through to the distance path, like git describe."""
        wd.commit_testfile()
        wd.create_tag("v1.2.3")
        wd.commit_testfile()
        wd.create_tag("event-2024")
        wd("hg update -r event-2024")

        assert version_for(wd, None) == "2024"
        assert version_for(wd, False) == "2024"
        strict = version_for(wd, True)
        assert strict.startswith("1.2.4.dev"), strict

    def test_version_tag_wins_among_several_on_one_changeset(self, wd: WorkDir) -> None:
        """hg lists several tags per changeset; strict must not pick by order."""
        wd.commit_testfile()
        wd("hg tag -r 0 v1.2.3")
        wd("hg tag -r 0 event-2024")
        wd("hg update -r 0")

        assert version_for(wd, None) == "2024"
        assert version_for(wd, True) == "1.2.3"

    def test_version_tag_on_head_is_kept_when_strict(self, wd: WorkDir) -> None:
        wd.commit_testfile()
        wd.create_tag("v1.2.3")
        wd("hg update -r v1.2.3")

        assert version_for(wd, None) == "1.2.3"
        assert version_for(wd, True) == "1.2.3"


class TestStrictOnDistancePath:
    def test_event_tag_shadows_version_tag(self, wd: WorkDir) -> None:
        wd.commit_testfile()
        wd.create_tag("v1.2.3")
        wd.commit_testfile()
        wd.create_tag("event-2024")
        wd.commit_testfile()

        assert version_for(wd, None).startswith("2025.dev")
        assert version_for(wd, True).startswith("1.2.4.dev")


class TestStrictDiagnostic:
    def test_warns_when_the_future_default_differs(
        self, wd: WorkDir, caplog: pytest.LogCaptureFixture
    ) -> None:
        wd.commit_testfile()
        wd.create_tag("v1.2.3")
        wd.commit_testfile()
        wd.create_tag("event-2024")
        wd.commit_testfile()

        with caplog.at_level(logging.WARNING):
            version_for(wd, None)

        (message,) = [m for m in reported(caplog) if "tag.strict" in m]
        assert "event-2024" in message
        assert "v1.2.3" in message

    def test_warns_on_a_tagged_changeset_too(
        self, wd: WorkDir, caplog: pytest.LogCaptureFixture
    ) -> None:
        wd.commit_testfile()
        wd("hg tag -r 0 v1.2.3")
        wd("hg tag -r 0 event-2024")
        wd("hg update -r 0")

        with caplog.at_level(logging.WARNING):
            version_for(wd, None)

        (message,) = [m for m in reported(caplog) if "tag.strict" in m]
        assert "2024 (from tag 'event-2024')" in message
        assert "1.2.3 (from tag 'v1.2.3')" in message

    def test_silent_for_plain_version_tags(
        self, wd: WorkDir, caplog: pytest.LogCaptureFixture
    ) -> None:
        wd.commit_testfile()
        wd.create_tag("v1.2.3")
        wd.commit_testfile()

        with caplog.at_level(logging.WARNING):
            version_for(wd, None)

        assert [m for m in reported(caplog) if "tag.strict" in m] == []

    def test_silent_without_any_tags(
        self, wd: WorkDir, caplog: pytest.LogCaptureFixture
    ) -> None:
        wd.commit_testfile()

        with caplog.at_level(logging.WARNING):
            version_for(wd, None)

        assert [m for m in reported(caplog) if "tag.strict" in m] == []

    @pytest.mark.parametrize("strict", [True, False])
    def test_silent_when_strict_is_set(
        self, wd: WorkDir, caplog: pytest.LogCaptureFixture, strict: bool
    ) -> None:
        """Setting the option explicitly is the way to silence the notice."""
        wd.commit_testfile()
        wd.create_tag("v1.2.3")
        wd.commit_testfile()
        wd.create_tag("event-2024")
        wd.commit_testfile()

        with caplog.at_level(logging.WARNING):
            version_for(wd, strict)

        assert [m for m in reported(caplog) if "tag.strict" in m] == []
