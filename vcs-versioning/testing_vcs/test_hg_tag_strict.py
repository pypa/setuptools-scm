"""Tests for ``tag.strict`` on the Mercurial backend.

Covers both the behaviour (strict must apply to the tags on the current
changeset, not just to the distance path) and the divergence diagnostic --
see #1495, follow-up to #1429.
"""

from __future__ import annotations

import logging

import pytest
from vcs_versioning import Configuration
from vcs_versioning._backends._hg import hg_tag_pattern, matches_tag_pattern, select_tag
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


class TestSelectTag:
    """Which tag wins among the tags on the current changeset (#1495).

    Pure selection logic, so it is exercised directly rather than through a
    repository -- hg puts several tags on one changeset routinely and the
    ordering it reports them in is not something to build a test around.
    """

    def config(self, **tag_kw: object) -> Configuration:
        return Configuration(tag=TagConfiguration(**tag_kw))  # type: ignore[arg-type]

    def test_event_tag_rejected_when_strict(self) -> None:
        """Strict leaves the changeset untagged, so versioning falls through."""
        config = self.config(strict=None)
        assert select_tag(["event-2024"], config, strict=False) == "event-2024"
        assert select_tag(["event-2024"], config, strict=True) is None

    def test_version_tag_wins_over_event_tag_when_strict(self) -> None:
        """hg reports several tags per changeset; order must not decide."""
        config = self.config(strict=None)
        tags = ["event-2024", "v1.2.3"]
        assert select_tag(tags, config, strict=False) == "event-2024"
        assert select_tag(tags, config, strict=True) == "v1.2.3"

    def test_order_does_not_matter_under_strict(self) -> None:
        config = self.config(strict=None)
        assert select_tag(["v1.2.3", "event-2024"], config, strict=True) == "v1.2.3"

    def test_version_tag_kept_when_strict(self) -> None:
        config = self.config(strict=None)
        assert select_tag(["v1.2.3"], config, strict=True) == "v1.2.3"

    def test_non_version_tags_skipped_either_way(self) -> None:
        config = self.config(strict=None)
        assert select_tag(["nightly"], config, strict=False) is None
        assert select_tag(["nightly"], config, strict=True) is None

    def test_permissive_selection_is_unchanged(self) -> None:
        """The narrowing must only engage when strictness was asked for."""
        config = self.config(strict=None)
        tags = ["event-2024", "v1.2.3"]
        assert select_tag(tags, config) == select_tag(tags, config, strict=False)

    def test_prefix_is_stripped_before_matching(self) -> None:
        config = self.config(prefix="pkg-", strict=None)
        tags = ["pkg-2024", "pkg-1.2.3"]
        assert select_tag(tags, config, strict=False) == "pkg-2024"
        assert select_tag(tags, config, strict=True) == "pkg-1.2.3"


class TestStrictOnTaggedChangeset:
    def test_event_tag_on_head_is_rejected_when_strict(self, wd: WorkDir) -> None:
        """End to end: strict continues from the last real version tag."""
        wd.commit_testfile()
        wd('hg tag v1.2.3 -u test -d "0 0"')
        wd.commit_testfile()
        wd('hg tag event-2024 -u test -d "0 0"')
        wd("hg up -C event-2024")

        # state the precondition, so a checkout that did not land where we
        # expect reports that rather than an unexplained version mismatch
        assert "event-2024" in wd('hg log -r . -T "{tags}"')

        assert version_for(wd, False).startswith("2024")
        assert version_for(wd, True).startswith("1.2.4.dev")


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
