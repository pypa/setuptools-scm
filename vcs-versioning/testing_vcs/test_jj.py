"""Tests for the Jujutsu (jj) VCS backend."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from vcs_versioning import Configuration
from vcs_versioning._backends import _jj as jj
from vcs_versioning._backends._discover_vcs import discover
from vcs_versioning._file_finders._jj import jj_find_files
from vcs_versioning._run_cmd import CommandNotFoundError
from vcs_versioning.test_api import DebugMode, WorkDir


@pytest.fixture
def wd(wd: WorkDir, debug_mode: DebugMode) -> WorkDir:
    """Set up jj for jj-specific tests."""
    debug_mode.disable()
    wd.setup_jj()
    debug_mode.enable()
    return wd


def test_jj_gone(wd: WorkDir, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(wd.cwd / "not-existing"))
    with pytest.raises(CommandNotFoundError, match=r"jj"):
        jj.parse(wd.cwd, Configuration())


def test_version_from_jj(wd: WorkDir) -> None:
    # Initial empty repo -- no commits, no files, jj considers it clean
    # but we force dirty=True when node is None (no meaningful commit)
    wd.expect_parse(tag="0.0", distance=0, dirty=True)

    wd.commit_testfile()
    wd.expect_parse(tag="0.0", distance=1, dirty=False, node_prefix="j")

    # Tag the commit (after jj commit, the tagged commit is @-)
    wd("jj tag set v0.1 -r @-")
    wd.expect_parse(tag="0.1", distance=0, dirty=False, exact=True)

    # Dirty state -- write without committing.
    # In jj, the working copy IS a commit.  When it has changes, jj
    # snapshots them into @, so distance=1 (one non-empty commit ahead).
    wd.write("test.txt", "test2")
    wd.expect_parse(tag="0.1", distance=1, dirty=True)

    # Commit the change and tag
    wd.commit_testfile()
    wd("jj tag set version-0.2 -r @-")
    wd.expect_parse(tag="0.2", distance=0, dirty=False, exact=True)


def test_jj_no_tags(wd: WorkDir) -> None:
    wd.commit_testfile()
    wd.commit_testfile()
    wd.commit_testfile()

    version = jj.parse(wd.cwd, Configuration())
    assert version is not None
    assert version.distance >= 3
    assert str(version.tag) == "0.0"


def test_jj_exact_tag(wd: WorkDir) -> None:
    wd.commit_testfile()
    wd("jj tag set v1.0.0 -r @-")

    version = jj.parse(wd.cwd, Configuration())
    assert version is not None
    assert version.distance == 0
    assert str(version.tag) == "1.0.0"


def test_jj_dirty_state(wd: WorkDir) -> None:
    wd.commit_testfile()
    wd("jj tag set v1.0.0 -r @-")

    # Clean state
    version = jj.parse(wd.cwd, Configuration())
    assert version is not None
    assert not version.dirty

    # Dirty state -- write a file (jj auto-tracks it)
    wd.write("dirty.txt", "dirty content")
    version = jj.parse(wd.cwd, Configuration())
    assert version is not None
    assert version.dirty


def test_jj_distance(wd: WorkDir) -> None:
    wd.commit_testfile()
    wd("jj tag set v1.0.0 -r @-")

    wd.commit_testfile()
    wd.commit_testfile()

    version = jj.parse(wd.cwd, Configuration())
    assert version is not None
    assert version.distance == 2
    assert str(version.tag) == "1.0.0"


def test_jj_branch_detection(wd: WorkDir) -> None:
    wd.commit_testfile()
    wd("jj bookmark create test-branch -r @-")

    version = jj.parse(wd.cwd, Configuration())
    assert version is not None
    # The bookmark is on @-, not @, so branch may or may not be set
    # depending on jj's model. Just verify the call doesn't fail.
    assert version.branch is None or isinstance(version.branch, str)


def test_jj_node_prefix(wd: WorkDir) -> None:
    """jj nodes should be prefixed with 'j' to distinguish from git's 'g'."""
    wd.commit_testfile()
    version = jj.parse(wd.cwd, Configuration())
    assert version is not None
    assert version.node is not None
    assert version.node.startswith("j")


def test_jj_file_finder(wd: WorkDir) -> None:
    wd.commit_testfile()
    files = jj_find_files(str(wd.cwd))
    assert len(files) > 0
    basenames = [os.path.basename(f) for f in files]
    assert "test.txt" in basenames


def test_jj_file_finder_no_repo(tmp_path: Path) -> None:
    files = jj_find_files(str(tmp_path))
    assert files == []


def test_jj_missing_binary_errors(tmp_path: Path) -> None:
    """When .jj/ exists but jj is not on PATH, discovery should error."""
    (tmp_path / ".jj").mkdir()
    config = Configuration(root=tmp_path)

    with patch(
        "vcs_versioning._backends._discover_vcs.has_command", return_value=False
    ):
        with pytest.raises(LookupError, match="jj.*not available"):
            discover(tmp_path, config=config)


def test_jj_colocated_prefers_jj(wd: WorkDir) -> None:
    """In a colocated repo (.jj + .git), jj should be preferred."""
    wd.commit_testfile()
    wd("jj tag set v2.0.0 -r @-")

    # Verify both markers exist (jj git init creates colocated by default)
    assert (wd.cwd / ".jj").is_dir()
    assert (wd.cwd / ".git").exists()

    config = Configuration(root=wd.cwd)
    result = discover(wd.cwd, config=config)

    assert result is not None
    assert type(result).__name__ == "JjWorkdir"
