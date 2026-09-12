"""Path-restricted distance counting for monorepo projects (:issue:`1056`).

``git describe`` always counts every commit since the tag, so a project living
in a subdirectory of a monorepo has its version moved by its siblings' commits.
``scm.git.distance_scope`` restricts the count to the commits that touch the
project (and optionally further shared directories).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from vcs_versioning import Configuration
from vcs_versioning._backends._git import (
    GitDistanceCount,
    archival_to_version,
    resolve_scope_paths,
)
from vcs_versioning._config import GitConfiguration
from vcs_versioning._scm_version import ScmVersion
from vcs_versioning._test_utils import WorkDir

PKG_A = "packages/pkg-a"
PKG_B = "packages/pkg-b"


@pytest.fixture
def wd(wd: WorkDir, monkeypatch: pytest.MonkeyPatch) -> WorkDir:
    wd.setup_git(monkeypatch)
    return wd


def reported(caplog: pytest.LogCaptureFixture) -> list[str]:
    """Messages of warning-or-worse records; debug logging is noise here."""
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


def touch(wd: WorkDir, path: str, reason: str) -> None:
    """Commit a change to *path* so that exactly that path is touched."""
    wd.write(f"{path}/f.txt", reason)
    wd.add_and_commit(reason)


def project_version(
    wd: WorkDir, project: str = PKG_A, tag_prefix: str = "", **git_kw: object
) -> ScmVersion:
    """The ``ScmVersion`` a project inside the monorepo infers."""
    pyproject = wd.cwd / project / "pyproject.toml"
    pyproject.parent.mkdir(parents=True, exist_ok=True)
    if not pyproject.is_file():
        pyproject.write_text('[project]\nname = "x"\n', encoding="utf-8")
    depth = len(Path(project).parts)
    config = Configuration(relative_to=str(pyproject), root="/".join([".."] * depth))
    config.tag.prefix = tag_prefix
    for key, value in git_kw.items():
        setattr(config.scm.git, key, value)
    workdir = config.discover_workdir()
    assert workdir is not None
    version = workdir.get_scm_version()
    assert version is not None
    return version


@pytest.fixture
def monorepo(wd: WorkDir) -> WorkDir:
    """A tagged monorepo where pkg-b moves but pkg-a does not.

    ``v1.0`` -- b0 -- b1 -- b2 -- a0 -- a1
    """
    touch(wd, PKG_A, "initial")
    wd.create_tag("v1.0")
    for i in range(3):
        touch(wd, PKG_B, f"b{i}")
    for i in range(2):
        touch(wd, PKG_A, f"a{i}")
    return wd


class TestDistanceScope:
    def test_unscoped_counts_sibling_commits(self, monorepo: WorkDir) -> None:
        """The behaviour #1056 complains about, pinned so the fix is visible."""
        assert project_version(monorepo).distance == 5

    def test_scoped_counts_only_own_commits(self, monorepo: WorkDir) -> None:
        version = project_version(monorepo, distance_scope=True)
        assert version.distance == 2

    def test_empty_list_is_the_same_as_true(self, monorepo: WorkDir) -> None:
        assert project_version(monorepo, distance_scope=[]).distance == 2

    def test_extra_paths_also_count(self, monorepo: WorkDir) -> None:
        """Shared directories a project depends on can move its version too."""
        version = project_version(monorepo, distance_scope=[PKG_B])
        assert version.distance == 5

    def test_extra_path_that_never_changed_adds_nothing(
        self, monorepo: WorkDir
    ) -> None:
        version = project_version(monorepo, distance_scope=["tooling"])
        assert version.distance == 2

    def test_unchanged_project_is_exact(self, wd: WorkDir) -> None:
        """A project untouched since the tag is genuinely at that version."""
        touch(wd, PKG_A, "initial")
        wd.create_tag("v1.0")
        touch(wd, PKG_B, "b0")

        version = project_version(wd, distance_scope=True)
        assert version.distance == 0
        assert version.exact

    def test_dirty_is_scoped_too(self, monorepo: WorkDir) -> None:
        """Uncommitted changes in a sibling must not dirty this project."""
        monorepo.write(f"{PKG_B}/f.txt", "uncommitted")

        assert project_version(monorepo, distance_scope=True).dirty is False
        assert project_version(monorepo).dirty is True

    def test_dirty_in_own_path_still_counts(self, monorepo: WorkDir) -> None:
        monorepo.write(f"{PKG_A}/f.txt", "uncommitted")

        assert project_version(monorepo, distance_scope=True).dirty is True

    def test_untagged_repository_counts_own_history(self, wd: WorkDir) -> None:
        """Without any tag the fallback counts commits, and scoping applies."""
        touch(wd, PKG_B, "b0")
        touch(wd, PKG_A, "a0")
        touch(wd, PKG_B, "b1")

        version = project_version(wd, distance_scope=True)
        assert version.distance == 1

    def test_project_at_vcs_root_is_rejected(self, wd: WorkDir) -> None:
        """Scoping to the VCS root would be a silent no-op, so refuse it."""
        touch(wd, PKG_A, "initial")
        wd.create_tag("v1.0")

        config = Configuration(root=str(wd.cwd))
        config.scm.git.distance_scope = True
        workdir = config.discover_workdir()
        assert workdir is not None
        with pytest.raises(ValueError, match="would be a no-op"):
            workdir.get_scm_version()


class TestCountingPolicy:
    """Merge handling, where the policies actually differ."""

    @pytest.fixture
    def ours_merge(self, wd: WorkDir) -> WorkDir:
        """A topic branch touching pkg-a, merged with ``-s ours``.

        The merge keeps mainline's content for pkg-a, so git's *default*
        history simplification follows only the first parent and discards the
        topic branch -- which makes the distance shrink across the merge.
        """
        touch(wd, PKG_A, "initial")
        wd("git branch -M main")
        wd.create_tag("v1.0")
        touch(wd, PKG_A, "m0")
        wd("git checkout -q -b topic v1.0")
        for i in range(3):
            touch(wd, PKG_A, f"t{i}")
        wd("git checkout -q main")
        wd("git merge -q -s ours topic -m merge")
        return wd

    def test_full_history_counts_both_sides(self, ours_merge: WorkDir) -> None:
        version = project_version(ours_merge, distance_scope=True)
        # m0, t0, t1, t2, plus the merge -- it differs from its *topic* parent,
        # having discarded that side's content.
        assert version.distance == 5

    def test_first_parent_counts_mainline_only(self, ours_merge: WorkDir) -> None:
        version = project_version(
            ours_merge,
            distance_scope=True,
            distance_count=GitDistanceCount.FIRST_PARENT,
        )
        # Only m0.  The merge is compared against its first parent alone, and
        # ``-s ours`` kept exactly that content, so it counts as no change --
        # the same merge that ``full-history`` counts.
        assert version.distance == 1

    def test_full_history_does_not_shrink_across_a_merge(
        self, ours_merge: WorkDir
    ) -> None:
        """The property a version number depends on.

        ``HEAD`` is a descendant of ``topic``, so its distance must not be
        smaller.  Git's default simplification reports 3 for topic and 2 for
        the merge; ``--full-history`` is a set predicate and cannot regress.
        """
        at_merge = project_version(ours_merge, distance_scope=True).distance
        ours_merge("git checkout -q topic")
        at_topic = project_version(ours_merge, distance_scope=True).distance

        assert at_topic == 3
        assert at_merge >= at_topic

    def test_merge_of_unrelated_branch_is_not_counted(self, wd: WorkDir) -> None:
        """A merge that leaves the project's tree alone must not bump it."""
        touch(wd, PKG_A, "initial")
        wd("git branch -M main")
        wd.create_tag("v1.0")
        wd("git checkout -q -b side")
        touch(wd, PKG_B, "b0")
        wd("git checkout -q main")
        wd("git merge -q --no-ff side -m merge")

        assert project_version(wd, distance_scope=True).distance == 0


class TestTagNamespaceDiagnostic:
    """Per-project tags that an unfiltered describe would cross (:issue:`1056`)."""

    @pytest.fixture
    def namespaced_tags(self, wd: WorkDir) -> WorkDir:
        touch(wd, PKG_A, "initial")
        wd.create_tag("pkg-a-v1.0")
        touch(wd, PKG_B, "b0")
        wd.create_tag("pkg-b-v3.0")
        touch(wd, PKG_A, "a0")
        return wd

    def test_warns_when_tags_span_namespaces(
        self, namespaced_tags: WorkDir, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING):
            project_version(namespaced_tags, distance_scope=True)

        assert any("several project namespaces" in m for m in reported(caplog))

    def test_silent_for_a_single_release_train(
        self, monorepo: WorkDir, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Global ``v1.0``-style tags are unambiguous; do not nag."""
        with caplog.at_level(logging.WARNING):
            project_version(monorepo, distance_scope=True)

        assert not [m for m in reported(caplog) if "namespaces" in m]

    def test_silent_when_unscoped(
        self, namespaced_tags: WorkDir, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The diagnostic is about scoped counting only."""
        with caplog.at_level(logging.WARNING):
            project_version(namespaced_tags)

        assert not [m for m in reported(caplog) if "namespaces" in m]

    def test_tag_prefix_silences_it(
        self, namespaced_tags: WorkDir, caplog: pytest.LogCaptureFixture
    ) -> None:
        """With a prefix set, describe only ever sees this project's tags."""
        with caplog.at_level(logging.WARNING):
            version = project_version(
                namespaced_tags, tag_prefix="pkg-a-", distance_scope=True
            )

        assert not [m for m in reported(caplog) if "namespaces" in m]
        assert version.distance == 1


class TestShallow:
    def test_scoped_count_refuses_a_shallow_clone(
        self, monorepo: WorkDir, tmp_path: Path
    ) -> None:
        """A truncated history can miss every relevant commit and report zero."""
        clone = tmp_path / "shallow"
        # A list command, and as_uri() for the source: shlex.split() eats the
        # backslashes of a windows path, and --depth needs a file:// URL to
        # produce a shallow clone at all.
        monorepo(
            [
                *("git", "clone", "-q"),
                *("--depth", "1"),
                monorepo.cwd.as_uri(),
                str(clone),
            ]
        )
        assert (clone / ".git" / "shallow").is_file(), "clone was not shallow"
        shallow = WorkDir(clone)
        shallow.configure_git_commands()

        with pytest.raises(ValueError, match="shallow"):
            project_version(shallow, distance_scope=True)


class TestUnsupportedWorkdir:
    def test_hg_git_refuses_rather_than_counting_zero(self) -> None:
        """``GitWorkdirHgClient`` subclasses ``GitWorkdir`` but emulates describe.

        It inherits ``run_git``, which points at a ``.git`` directory that does
        not exist in an hg-git checkout -- the inherited count would fail and
        fall back to 0, reading as an exact tag.  Refuse instead.
        """

        class Unsupported:
            supports_distance_scope = False
            path = Path("/repo")
            project_path = "packages/pkg-a"

        config = Configuration()
        config.scm.git.distance_scope = True
        with pytest.raises(ValueError, match="git-only feature"):
            resolve_scope_paths(Unsupported(), config)  # type: ignore[arg-type]


class TestConfigurationParsing:
    """``scm.git`` values as they arrive from ``pyproject.toml``."""

    def test_distance_scope_accepts_bool(self) -> None:
        config = GitConfiguration.from_data({"distance_scope": True})
        assert config.scope_paths == []

    def test_distance_scope_accepts_paths(self) -> None:
        config = GitConfiguration.from_data({"distance_scope": ["shared", "tools"]})
        assert config.scope_paths == ["shared", "tools"]

    def test_distance_scope_defaults_to_off(self) -> None:
        assert GitConfiguration.from_data({}).scope_paths is None

    def test_distance_scope_rejects_absolute_paths(self) -> None:
        with pytest.raises(ValueError, match="relative to the VCS root"):
            GitConfiguration.from_data({"distance_scope": ["/etc"]})

    def test_distance_scope_rejects_other_types(self) -> None:
        with pytest.raises(ValueError, match="must be a boolean or a list"):
            GitConfiguration.from_data({"distance_scope": "packages/pkg-a"})

    def test_distance_count_accepts_the_policy_names(self) -> None:
        config = GitConfiguration.from_data({"distance_count": "first-parent"})
        assert config.distance_count is GitDistanceCount.FIRST_PARENT

    def test_distance_count_defaults_to_full_history(self) -> None:
        config = GitConfiguration.from_data({})
        assert config.distance_count is GitDistanceCount.FULL_HISTORY

    def test_distance_count_rejects_git_default_simplification(self) -> None:
        """Deliberately unsupported -- it can make the distance shrink."""
        with pytest.raises(ValueError, match="Invalid git distance_count"):
            GitConfiguration.from_data({"distance_count": "git-default"})


class TestArchivalOvershoot:
    """``git archive`` can only record a repository-wide distance (:issue:`1056`).

    ``%(describe)`` takes no pathspec, so an archive of a non-tag commit carries
    a count that is an upper bound on the scoped one.
    """

    @staticmethod
    def archival(describe_name: str) -> dict[str, str]:
        return {
            "node": "1" * 40,
            "node-date": "2024-01-01T00:00:00+00:00",
            "describe-name": describe_name,
            "ref-names": "HEAD -> main",
        }

    def make_config(self, **git_kw: object) -> Configuration:
        config = Configuration()
        for key, value in git_kw.items():
            setattr(config.scm.git, key, value)
        return config

    def test_tagged_archive_is_exact_and_silent(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The release-tarball case: distance 0 scoped and unscoped alike."""
        config = self.make_config(distance_scope=True)
        with caplog.at_level(logging.WARNING):
            version = archival_to_version(self.archival("v1.0"), config)

        assert version is not None
        assert version.distance == 0
        assert not [m for m in reported(caplog) if "upper bound" in m]

    def test_untagged_archive_warns_about_the_overshoot(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        config = self.make_config(distance_scope=True)
        with caplog.at_level(logging.WARNING):
            version = archival_to_version(self.archival("v1.0-7-gabcdef1"), config)

        assert version is not None
        # Still usable -- too high, never too low.
        assert version.distance == 7
        assert any("upper bound" in m for m in reported(caplog))

    def test_untagged_archive_silent_when_unscoped(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        config = self.make_config()
        with caplog.at_level(logging.WARNING):
            version = archival_to_version(self.archival("v1.0-7-gabcdef1"), config)

        assert version is not None
        assert version.distance == 7
        assert not [m for m in reported(caplog) if "upper bound" in m]
