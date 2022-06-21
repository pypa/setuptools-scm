from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import date
from datetime import datetime
from datetime import timezone
from os.path import join as opj
from pathlib import Path
from textwrap import dedent
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from .wd_wrapper import WorkDir
from setuptools_scm import Configuration
from setuptools_scm import format_version
from setuptools_scm import git
from setuptools_scm import integration
from setuptools_scm import NonNormalizedVersion
from setuptools_scm.file_finder_git import git_find_files
from setuptools_scm.git import archival_to_version
from setuptools_scm.utils import do
from setuptools_scm.utils import has_command

pytestmark = pytest.mark.skipif(
    not has_command("git", warn=False), reason="git executable not found"
)


@pytest.fixture
def wd(wd: WorkDir, monkeypatch: pytest.MonkeyPatch) -> WorkDir:
    monkeypatch.delenv("HOME", raising=False)
    wd("git init")
    wd("git config user.email test@example.com")
    wd('git config user.name "a test"')
    wd.add_command = "git add ."
    wd.commit_command = "git commit -m test-{reason}"
    return wd


@pytest.mark.parametrize(
    "given, tag, number, node, dirty",
    [
        ("3.3.1-rc26-0-g9df187b", "3.3.1-rc26", 0, "g9df187b", False),
        ("17.33.0-rc-17-g38c3047c0", "17.33.0-rc", 17, "g38c3047c0", False),
    ],
)
def test_parse_describe_output(
    given: str, tag: str, number: int, node: str, dirty: bool
) -> None:
    parsed = git._git_parse_describe(given)
    assert parsed == (tag, number, node, dirty)


def test_root_relative_to(wd: WorkDir, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")
    p = wd.cwd.joinpath("sub/package")
    p.mkdir(parents=True)
    p.joinpath("setup.py").write_text(
        """from setuptools import setup
setup(use_scm_version={"root": "../..",
                       "relative_to": __file__})
"""
    )
    res = do([sys.executable, "setup.py", "--version"], p)
    assert res == "0.1.dev0"


def test_root_search_parent_directories(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")
    p = wd.cwd.joinpath("sub/package")
    p.mkdir(parents=True)
    p.joinpath("setup.py").write_text(
        """from setuptools import setup
setup(use_scm_version={"search_parent_directories": True})
"""
    )
    res = do([sys.executable, "setup.py", "--version"], p)
    assert res == "0.1.dev0"


def test_git_gone(wd: WorkDir, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(wd.cwd / "not-existing"))
    with pytest.raises(EnvironmentError, match="'git' was not found"):
        git.parse(str(wd.cwd), git.DEFAULT_DESCRIBE)


@pytest.mark.issue("https://github.com/pypa/setuptools_scm/issues/298")
@pytest.mark.issue(403)
def test_file_finder_no_history(wd: WorkDir, caplog: pytest.LogCaptureFixture) -> None:
    file_list = git_find_files(str(wd.cwd))
    assert file_list == []

    assert "listing git files failed - pretending there aren't any" in caplog.text


@pytest.mark.issue("https://github.com/pypa/setuptools_scm/issues/281")
def test_parse_call_order(wd: WorkDir) -> None:
    git.parse(str(wd.cwd), git.DEFAULT_DESCRIBE)


@pytest.mark.issue("https://github.com/pypa/setuptools_scm/issues/707")
@pytest.mark.xfail(run=False, reason="This test requires passwordless sudo")
def test_not_owner(wd: WorkDir) -> None:
    git_dir = opj(wd.cwd)
    original_stat = os.stat(git_dir)
    if not shutil.which("sudo"):
        pytest.skip("sudo executable not found")

    proc = subprocess.run(
        ["sudo", "chown", "-R", "12345", git_dir], stdin=subprocess.DEVNULL
    )
    if proc.returncode != 0:
        pytest.skip("Failed to change ownership, is passwordless sudo available?")
    try:
        subprocess.run(
            ["sudo", "chmod", "a+r", git_dir], stdin=subprocess.DEVNULL, check=True
        )
        subprocess.run(
            ["sudo", "chgrp", "-R", "12345", git_dir],
            stdin=subprocess.DEVNULL,
            check=True,
        )
        assert git.parse(str(wd.cwd))
    finally:
        # Restore the ownership
        subprocess.run(
            ["sudo", "chown", "-R", str(original_stat.st_uid), git_dir],
            stdin=subprocess.DEVNULL,
            check=True,
        )
        subprocess.run(
            ["sudo", "chgrp", "-R", str(original_stat.st_gid), git_dir],
            stdin=subprocess.DEVNULL,
            check=True,
        )


def test_version_from_git(wd: WorkDir) -> None:
    assert wd.version == "0.1.dev0"

    parsed = git.parse(str(wd.cwd), git.DEFAULT_DESCRIBE)
    assert parsed is not None and parsed.branch == "master"

    wd.commit_testfile()
    assert wd.version.startswith("0.1.dev1+g")
    assert not wd.version.endswith("1-")

    wd("git tag v0.1")
    assert wd.version == "0.1"

    wd.write("test.txt", "test2")
    assert wd.version.startswith("0.2.dev0+g")

    wd.commit_testfile()
    assert wd.version.startswith("0.2.dev1+g")

    wd("git tag version-0.2")
    assert wd.version.startswith("0.2")

    wd.commit_testfile()
    wd("git tag version-0.2.post210+gbe48adfpost3+g0cc25f2")
    with pytest.warns(
        UserWarning, match="tag '.*' will be stripped of its suffix '.*'"
    ):
        assert wd.version.startswith("0.2")

    wd.commit_testfile()
    wd("git tag 17.33.0-rc")
    assert wd.version == "17.33.0rc0"

    # custom normalization
    assert wd.get_version(normalize=False) == "17.33.0-rc"
    assert wd.get_version(version_cls=NonNormalizedVersion) == "17.33.0-rc"
    assert (
        wd.get_version(version_cls="setuptools_scm.NonNormalizedVersion")
        == "17.33.0-rc"
    )


setup_py_with_normalize: dict[str, str] = {
    "false": """
        from setuptools import setup
        setup(use_scm_version={'normalize': False, 'write_to': 'VERSION.txt'})
        """,
    "with_created_class": """
        from setuptools import setup

        class MyVersion:
            def __init__(self, tag_str: str):
                self.version = tag_str

            def __repr__(self):
                return self.version

        setup(use_scm_version={'version_cls': MyVersion, 'write_to': 'VERSION.txt'})
        """,
    "with_named_import": """
        from setuptools import setup
        setup(use_scm_version={
            'version_cls': 'setuptools_scm.NonNormalizedVersion',
            'write_to': 'VERSION.txt'
        })
        """,
}


@pytest.mark.parametrize(
    "setup_py_txt",
    [pytest.param(text, id=key) for key, text in setup_py_with_normalize.items()],
)
def test_git_version_unnormalized_setuptools(
    setup_py_txt: str, wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Test that when integrating with setuptools without normalization,
    the version is not normalized in write_to files,
    but still normalized by setuptools for the final dist metadata.
    """
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")

    wd.write("setup.py", dedent(setup_py_txt))

    # do git operations and tag
    wd.commit_testfile()
    wd("git tag 17.33.0-rc1")

    # setuptools still normalizes using packaging.Version (removing the dash)
    res = wd([sys.executable, "setup.py", "--version"])
    assert res == "17.33.0rc1"

    # but the version tag in the file is non-normalized (with the dash)
    assert wd.cwd.joinpath("VERSION.txt").read_text() == "17.33.0-rc1"


@pytest.mark.issue(179)
def test_unicode_version_scheme(wd: WorkDir) -> None:
    scheme = b"guess-next-dev".decode("ascii")
    assert wd.get_version(version_scheme=scheme)


@pytest.mark.issue(108)
@pytest.mark.issue(109)
def test_git_worktree(wd: WorkDir) -> None:
    wd.write("test.txt", "test2")
    # untracked files dont change the state
    assert wd.version == "0.1.dev0"
    wd("git add test.txt")
    assert wd.version.startswith("0.1.dev0+d")


@pytest.mark.issue(86)
@pytest.mark.parametrize("today", [False, True])
def test_git_dirty_notag(
    today: bool, wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    if today:
        monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    wd.commit_testfile()
    wd.write("test.txt", "test2")
    wd("git add test.txt")
    assert wd.version.startswith("0.1.dev1")
    if today:
        # the date on the tag is in UTC
        tag = datetime.now(timezone.utc).date().strftime(".d%Y%m%d")
    else:
        tag = ".d20090213"
    # we are dirty, check for the tag
    assert tag in wd.version


@pytest.mark.issue(193)
@pytest.mark.xfail(reason="sometimes relative path results")
def test_git_worktree_support(wd: WorkDir, tmp_path: Path) -> None:
    wd.commit_testfile()
    worktree = tmp_path / "work_tree"
    wd("git worktree add -b work-tree %s" % worktree)

    res = do([sys.executable, "-m", "setuptools_scm", "ls"], cwd=worktree)
    assert "test.txt" in res
    assert str(worktree) in res


@pytest.fixture
def shallow_wd(wd: WorkDir, tmp_path: Path) -> Path:
    wd.commit_testfile()
    wd.commit_testfile()
    wd.commit_testfile()
    target = tmp_path / "wd_shallow"
    do(["git", "clone", "file://%s" % wd.cwd, str(target), "--depth=1"])
    return target


def test_git_parse_shallow_warns(
    shallow_wd: Path, recwarn: pytest.WarningsRecorder
) -> None:
    git.parse(str(shallow_wd))
    msg = recwarn.pop()
    assert "is shallow and may cause errors" in str(msg.message)


def test_git_parse_shallow_fail(shallow_wd: Path) -> None:
    with pytest.raises(ValueError, match="git fetch"):
        git.parse(str(shallow_wd), pre_parse=git.fail_on_shallow)


def test_git_shallow_autocorrect(
    shallow_wd: Path, recwarn: pytest.WarningsRecorder
) -> None:
    git.parse(str(shallow_wd), pre_parse=git.fetch_on_shallow)
    msg = recwarn.pop()
    assert "git fetch was used to rectify" in str(msg.message)
    git.parse(str(shallow_wd), pre_parse=git.fail_on_shallow)


def test_find_files_stop_at_root_git(wd: WorkDir) -> None:
    wd.commit_testfile()
    project = wd.cwd / "project"
    project.mkdir()
    project.joinpath("setup.cfg").touch()
    assert integration.find_files(str(project)) == []


@pytest.mark.issue(128)
def test_parse_no_worktree(tmp_path: Path) -> None:
    ret = git.parse(str(tmp_path))
    assert ret is None


def test_alphanumeric_tags_match(wd: WorkDir) -> None:
    wd.commit_testfile()
    wd("git tag newstyle-development-started")
    assert wd.version.startswith("0.1.dev1+g")


def test_git_archive_export_ignore(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    wd.write("test1.txt", "test")
    wd.write("test2.txt", "test")
    wd.write(
        ".git/info/attributes",
        # Explicitly include test1.txt so that the test is not affected by
        # a potentially global gitattributes file on the test machine.
        "/test1.txt -export-ignore\n/test2.txt export-ignore",
    )
    wd("git add test1.txt test2.txt")
    wd.commit()
    monkeypatch.chdir(wd.cwd)
    assert integration.find_files(".") == [opj(".", "test1.txt")]


@pytest.mark.issue(228)
def test_git_archive_subdirectory(wd: WorkDir, monkeypatch: pytest.MonkeyPatch) -> None:
    os.mkdir(wd.cwd / "foobar")
    wd.write("foobar/test1.txt", "test")
    wd("git add foobar")
    wd.commit()
    monkeypatch.chdir(wd.cwd)
    assert integration.find_files(".") == [opj(".", "foobar", "test1.txt")]


@pytest.mark.issue(251)
def test_git_archive_run_from_subdirectory(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    os.mkdir(wd.cwd / "foobar")
    wd.write("foobar/test1.txt", "test")
    wd("git add foobar")
    wd.commit()
    monkeypatch.chdir(wd.cwd / "foobar")
    assert integration.find_files(".") == [opj(".", "test1.txt")]


def test_git_feature_branch_increments_major(wd: WorkDir) -> None:
    wd.commit_testfile()
    wd("git tag 1.0.0")
    wd.commit_testfile()
    assert wd.get_version(version_scheme="python-simplified-semver").startswith("1.0.1")
    wd("git checkout -b feature/fun")
    wd.commit_testfile()
    assert wd.get_version(version_scheme="python-simplified-semver").startswith("1.1.0")


@pytest.mark.issue("https://github.com/pypa/setuptools_scm/issues/303")
def test_not_matching_tags(wd: WorkDir) -> None:
    wd.commit_testfile()
    wd("git tag apache-arrow-0.11.1")
    wd.commit_testfile()
    wd("git tag apache-arrow-js-0.9.9")
    wd.commit_testfile()
    assert wd.get_version(
        tag_regex=r"^apache-arrow-([\.0-9]+)$",
        git_describe_command="git describe --dirty --tags --long --exclude *js* ",
    ).startswith("0.11.2")


@pytest.mark.issue("https://github.com/pypa/setuptools_scm/issues/411")
@pytest.mark.xfail(reason="https://github.com/pypa/setuptools_scm/issues/449")
def test_non_dotted_version(wd: WorkDir) -> None:
    wd.commit_testfile()
    wd("git tag apache-arrow-1")
    wd.commit_testfile()
    assert wd.get_version().startswith("2")


def test_non_dotted_version_with_updated_regex(wd: WorkDir) -> None:
    wd.commit_testfile()
    wd("git tag apache-arrow-1")
    wd.commit_testfile()
    assert wd.get_version(tag_regex=r"^apache-arrow-([\.0-9]+)$").startswith("2")


def test_non_dotted_tag_no_version_match(wd: WorkDir) -> None:
    wd.commit_testfile()
    wd("git tag apache-arrow-0.11.1")
    wd.commit_testfile()
    wd("git tag apache-arrow")
    wd.commit_testfile()
    assert wd.get_version().startswith("0.11.2.dev2")


@pytest.mark.issue("https://github.com/pypa/setuptools_scm/issues/381")
def test_gitdir(monkeypatch: pytest.MonkeyPatch, wd: WorkDir) -> None:
    """ """
    wd.commit_testfile()
    normal = wd.version
    # git hooks set this and break subsequent setuptools_scm unless we clean
    monkeypatch.setenv("GIT_DIR", __file__)
    assert wd.version == normal


def test_git_getdate(wd: WorkDir) -> None:
    # TODO: case coverage for git wd parse
    today = date.today()

    def parse_date() -> date:
        parsed = git.parse(os.fspath(wd.cwd))
        assert parsed is not None
        assert parsed.node_date is not None
        return parsed.node_date

    git_wd = git.GitWorkdir(os.fspath(wd.cwd))
    assert git_wd.get_head_date() is None
    assert parse_date() == today

    wd.commit_testfile()
    assert git_wd.get_head_date() == today
    assert parse_date() == today


def test_git_getdate_badgit(wd: WorkDir) -> None:
    wd.commit_testfile()
    git_wd = git.GitWorkdir(os.fspath(wd.cwd))
    with patch.object(git_wd, "do_ex", Mock(return_value=("%cI", "", 0))):
        assert git_wd.get_head_date() is None


@pytest.fixture
def signed_commit_wd(monkeypatch: pytest.MonkeyPatch, wd: WorkDir) -> WorkDir:
    if not has_command("gpg", args=["--version"], warn=False):
        pytest.skip("gpg executable not found")

    wd.write(
        ".gpg_batch_params",
        """\
%no-protection
%transient-key
Key-Type: RSA
Key-Length: 2048
Name-Real: a test
Name-Email: test@example.com
Expire-Date: 0
""",
    )
    monkeypatch.setenv("GNUPGHOME", str(wd.cwd.resolve(strict=True)))
    wd("gpg --batch --generate-key .gpg_batch_params")

    wd("git config log.showSignature true")
    wd.signed_commit_command = "git commit -S -m test-{reason}"
    return wd


@pytest.mark.issue("https://github.com/pypa/setuptools_scm/issues/548")
def test_git_getdate_signed_commit(signed_commit_wd: WorkDir) -> None:
    today = date.today()
    signed_commit_wd.commit_testfile(signed=True)
    git_wd = git.GitWorkdir(os.fspath(signed_commit_wd.cwd))
    assert git_wd.get_head_date() == today


@pytest.mark.parametrize(
    "expected, from_data",
    [
        (
            "1.0",
            {"describe-name": "1.0-0-g0000"},
        ),
        (
            "1.1.dev3+g0000",
            {
                "describe-name": "1.0-3-g0000",
                "node": "0" * 20,
            },
        ),
        ("0.0", {"node": "0" * 20}),
        ("1.2.2", {"describe-name": "release-1.2.2-0-g00000"}),
        ("1.2.2.dev0", {"ref-names": "tag: release-1.2.2.dev"}),
    ],
)
@pytest.mark.filterwarnings("ignore:git archive did not support describe output")
def test_git_archival_to_version(expected: str, from_data: dict[str, str]) -> None:
    config = Configuration()
    version = archival_to_version(from_data, config=config)
    assert (
        format_version(
            version, version_scheme="guess-next-dev", local_scheme="node-and-date"
        )
        == expected
    )
