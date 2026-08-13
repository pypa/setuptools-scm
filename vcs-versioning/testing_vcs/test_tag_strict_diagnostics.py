"""Tests for the actionable ``tag.strict`` / ``describe_command`` diagnostics.

The diagnostics only fire when the setting in question actually changes the
version for the repository at hand -- see #1429.
"""

from __future__ import annotations

import fnmatch
import logging
from collections.abc import Sequence
from pathlib import Path

import pytest
from vcs_versioning import Configuration
from vcs_versioning._backends import _git
from vcs_versioning._config import TagConfiguration
from vcs_versioning._run_cmd import CompletedProcess
from vcs_versioning._test_utils import WorkDir


@pytest.fixture
def wd(wd: WorkDir, monkeypatch: pytest.MonkeyPatch) -> WorkDir:
    wd.setup_git(monkeypatch)
    return wd


def reported(caplog: pytest.LogCaptureFixture) -> list[str]:
    """Messages of warning-or-worse records; debug logging is noise here."""
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


def describe_output(tag: str, distance: int = 1, node: str = "abcdef1") -> str:
    return f"{tag}-{distance}-g{node}"


class FakeWorkdir:
    """Minimal stand-in providing the parts the diagnostics use."""

    def __init__(self, config: Configuration, results: dict[str, str]) -> None:
        self.config = config
        self.path = Path("/fake/repo")
        self.results = results
        self.calls: list[str] = []

    def run_git(self, args: Sequence[str]) -> CompletedProcess:
        args = list(args)
        match = args[args.index("--match") + 1]
        self.calls.append(match)
        stdout = self.results.get(match, "")
        return CompletedProcess(
            args=args, returncode=0 if stdout else 128, stdout=stdout, stderr=""
        )


def make_config(**tag_kw: object) -> Configuration:
    return Configuration(tag=TagConfiguration(**tag_kw))  # type: ignore[arg-type]


class TestStrictMatchGlob:
    """The strict glob must match a subset of the permissive one."""

    @pytest.mark.parametrize("prefix", ["", "v", "hatchling-v"])
    def test_glob_shape(self, prefix: str) -> None:
        assert _git._strict_match_glob(prefix) == f"{prefix}*[0-9]*.*[0-9]*"

    @pytest.mark.parametrize(
        ("tag", "matches"),
        [
            ("v1.2.3", True),
            ("1.0", True),
            ("1.2.3rc1", True),
            ("2024", False),
            ("event-2024", False),
            # a dot is not sufficient -- the glob needs a digit before it,
            # which is why "does the tag contain a dot" is not a valid shortcut
            ("rel.2024", False),
            ("nightly", False),
        ],
    )
    def test_strict_glob_membership(self, tag: str, matches: bool) -> None:
        assert fnmatch.fnmatchcase(tag, _git._strict_match_glob("")) is matches


class TestDescribeTag:
    @pytest.mark.parametrize(
        ("output", "expected"),
        [
            ("v1.2.3-0-gabcdef1", "v1.2.3"),
            ("v1.2.3-4-gabcdef1-dirty", "v1.2.3"),
            # tags may contain dashes themselves
            ("event-2024-1-gabcdef1", "event-2024"),
            # a node ending in hex letters must not be truncated
            ("v1.2.3-0-gabcddd-dirty", "v1.2.3"),
            ("", None),
            ("   ", None),
        ],
    )
    def test_describe_tag(self, output: str, expected: str | None) -> None:
        assert _git._describe_tag(output) == expected


class TestDescribeOutcome:
    def test_renders_version_and_tag(self) -> None:
        outcome = _git._describe_outcome(
            describe_output("v1.2.3"), make_config(strict=None)
        )
        assert outcome == "1.2.4.dev1+gabcdef1 (from tag 'v1.2.3')"

    def test_no_match_reports_fallback(self) -> None:
        outcome = _git._describe_outcome("", make_config(strict=None))
        assert "no matching tag" in outcome

    def test_unparsable_tag_does_not_raise(self) -> None:
        """A hypothetical must never raise, nor leak meta()'s own warning."""
        outcome = _git._describe_outcome(
            describe_output("nightly"), make_config(strict=None)
        )
        assert (
            outcome == "no usable version -- tag 'nightly' does not parse as a version"
        )

    def test_prefix_is_stripped(self) -> None:
        outcome = _git._describe_outcome(
            describe_output("hatchling-v1.2.3"), make_config(prefix="hatchling-v")
        )
        assert outcome.startswith("1.2.4.dev1+gabcdef1 (from tag 'hatchling-v1.2.3')")


class TestStrictDivergence:
    """`tag.strict` unset: warn only when the future default changes the version."""

    def test_silent_when_permissive_answer_is_already_strict(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        config = make_config(strict=None)
        wd = FakeWorkdir(config, {"*[0-9]*": describe_output("v1.2.3")})
        with caplog.at_level(logging.WARNING):
            _git._warn_if_strict_would_differ(
                wd, config, wd.run_git(["--match", "*[0-9]*"])
            )
        assert reported(caplog) == []
        # the shortcut must avoid the second describe entirely
        assert wd.calls == ["*[0-9]*"]

    def test_silent_when_nothing_matched(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        config = make_config(strict=None)
        wd = FakeWorkdir(config, {})
        with caplog.at_level(logging.WARNING):
            _git._warn_if_strict_would_differ(
                wd, config, wd.run_git(["--match", "*[0-9]*"])
            )
        assert reported(caplog) == []
        assert wd.calls == ["*[0-9]*"]

    def test_warns_when_strict_picks_another_tag(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        config = make_config(strict=None)
        wd = FakeWorkdir(
            config,
            {
                "*[0-9]*": describe_output("event-2024"),
                "*[0-9]*.*[0-9]*": describe_output("v1.2.3", distance=2),
            },
        )
        with caplog.at_level(logging.WARNING):
            _git._warn_if_strict_would_differ(
                wd, config, wd.run_git(["--match", "*[0-9]*"])
            )

        (message,) = reported(caplog)
        assert "tag.strict is not set" in message
        # both concrete versions have to be in the message
        assert "2025.dev1+gabcdef1 (from tag 'event-2024')" in message
        assert "1.2.4.dev2+gabcdef1 (from tag 'v1.2.3')" in message

    def test_warns_when_strict_matches_nothing(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        config = make_config(strict=None)
        wd = FakeWorkdir(config, {"*[0-9]*": describe_output("2024")})
        with caplog.at_level(logging.WARNING):
            _git._warn_if_strict_would_differ(
                wd, config, wd.run_git(["--match", "*[0-9]*"])
            )

        (message,) = reported(caplog)
        assert "no matching tag" in message

    def test_prefix_is_applied_to_the_strict_glob(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        config = make_config(prefix="pkg-", strict=None)
        wd = FakeWorkdir(config, {"pkg-*[0-9]*": describe_output("pkg-2024")})
        with caplog.at_level(logging.WARNING):
            _git._warn_if_strict_would_differ(
                wd, config, wd.run_git(["--match", "pkg-*[0-9]*"])
            )
        assert wd.calls == ["pkg-*[0-9]*", "pkg-*[0-9]*.*[0-9]*"]

    def test_reported_only_once_per_process(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A build constructs the configuration more than once."""
        config = make_config(strict=None)
        results = {
            "*[0-9]*": describe_output("event-2024"),
            "*[0-9]*.*[0-9]*": describe_output("v1.2.3"),
        }
        with caplog.at_level(logging.WARNING):
            for _ in range(3):
                wd = FakeWorkdir(config, results)
                _git._warn_if_strict_would_differ(
                    wd, config, wd.run_git(["--match", "*[0-9]*"])
                )
        assert len(reported(caplog)) == 1


class TestDescribeCommandOverridesStrict:
    """`describe_command` wins over `tag.strict` -- say so only when it matters."""

    def test_silent_when_they_agree(self, caplog: pytest.LogCaptureFixture) -> None:
        config = make_config(strict=True)
        wd = FakeWorkdir(config, {"*[0-9]*.*[0-9]*": describe_output("v1.2.3")})
        with caplog.at_level(logging.WARNING):
            _git._warn_if_describe_command_overrides_strict(
                wd, config, CompletedProcess([], 0, describe_output("v1.2.3"), "")
            )
        assert reported(caplog) == []

    def test_warns_when_they_disagree(self, caplog: pytest.LogCaptureFixture) -> None:
        config = make_config(strict=True)
        wd = FakeWorkdir(config, {"*[0-9]*.*[0-9]*": describe_output("v1.2.3")})
        with caplog.at_level(logging.WARNING):
            _git._warn_if_describe_command_overrides_strict(
                wd, config, CompletedProcess([], 0, describe_output("nightly"), "")
            )

        (message,) = reported(caplog)
        assert "describe_command takes precedence over tag.strict" in message
        assert "1.2.4.dev1+gabcdef1 (from tag 'v1.2.3')" in message
        # tag.prefix still strips prefixes, so it must never be blamed here
        assert "tag.prefix" not in message.split("Drop tag.strict")[0]


class TestIntegration:
    """End to end against real git repositories."""

    def test_event_tag_shadowing_version_tag_warns(
        self, wd: WorkDir, caplog: pytest.LogCaptureFixture
    ) -> None:
        wd.commit_testfile()
        wd("git tag v1.2.3")
        wd.commit_testfile()
        wd("git tag event-2024")

        with caplog.at_level(logging.WARNING):
            wd.get_version()

        messages = reported(caplog)
        assert any("tag.strict is not set" in m for m in messages), messages

    def test_plain_version_tags_stay_silent(
        self, wd: WorkDir, caplog: pytest.LogCaptureFixture
    ) -> None:
        wd.commit_testfile()
        wd("git tag v1.2.3")
        wd.commit_testfile()

        with caplog.at_level(logging.WARNING):
            wd.get_version()

        messages = reported(caplog)
        assert not any("tag.strict" in m for m in messages), messages

    def test_describe_command_suppresses_the_strict_nag(
        self, wd: WorkDir, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The #1422 configuration must not produce conflicting advice."""
        wd.commit_testfile()
        wd("git tag v1.2.3")
        wd.commit_testfile()
        wd("git tag event-2024")

        describe = "git describe --dirty --tags --long --match v[0-9]*"
        with caplog.at_level(logging.WARNING):
            wd.get_version(scm={"git": {"describe_command": describe}})

        messages = reported(caplog)
        assert not any("tag.strict is not set" in m for m in messages), messages
