from __future__ import annotations

import contextlib
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
from typing import Generator
from unittest.mock import Mock
from unittest.mock import patch

import pytest

import setuptools_scm._file_finders

from setuptools_scm import Configuration
from setuptools_scm import NonNormalizedVersion
from setuptools_scm import git
from setuptools_scm._file_finders.git import git_find_files
from setuptools_scm._run_cmd import CommandNotFoundError
from setuptools_scm._run_cmd import CompletedProcess
from setuptools_scm._run_cmd import has_command
from setuptools_scm._run_cmd import run
from setuptools_scm.git import archival_to_version
from setuptools_scm.version import format_version

from .conftest import DebugMode
from .wd_wrapper import WorkDir

pytestmark = pytest.mark.skipif(
    not has_command("git", warn=False), reason="git executable not found"
)


@pytest.fixture(name="wd")
def wd(wd: WorkDir, monkeypatch: pytest.MonkeyPatch, debug_mode: DebugMode) -> WorkDir:
    debug_mode.disable()
    monkeypatch.delenv("HOME", raising=False)
    wd("git init")
    wd("git config user.email test@example.com")
    wd('git config user.name "a test"')
    wd.add_command = "git add ."
    wd.commit_command = "git commit -m test-{reason}"
    debug_mode.enable()
    return wd


@pytest.mark.parametrize(
    ("given", "tag", "number", "node", "dirty"),
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
""",
        encoding="utf-8",
    )
    res = run([sys.executable, "setup.py", "--version"], p)
    assert res.stdout == "0.1.dev0+d20090213"


def test_root_search_parent_directories(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")
    p = wd.cwd.joinpath("sub/package")
    p.mkdir(parents=True)
    p.joinpath("setup.py").write_text(
        """from setuptools import setup
setup(use_scm_version={"search_parent_directories": True})
""",
        encoding="utf-8",
    )
    res = run([sys.executable, "setup.py", "--version"], p)
    assert res.stdout == "0.1.dev0+d20090213"


def test_git_gone(wd: WorkDir, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(wd.cwd / "not-existing"))

    wd.write("pyproject.toml", "[tool.setuptools_scm]")
    with pytest.raises(CommandNotFoundError, match=r"git"):
        git.parse(wd.cwd, Configuration(), git.DEFAULT_DESCRIBE)

    assert wd.get_version(fallback_version="1.0") == "1.0"


@pytest.mark.issue("https://github.com/pypa/setuptools-scm/issues/298")
@pytest.mark.issue(403)
def test_file_finder_no_history(wd: WorkDir, caplog: pytest.LogCaptureFixture) -> None:
    file_list = git_find_files(str(wd.cwd))
    assert file_list == []

    assert "listing git files failed - pretending there aren't any" in caplog.text


@pytest.mark.issue("https://github.com/pypa/setuptools-scm/issues/281")
def test_parse_call_order(wd: WorkDir) -> None:
    git.parse(str(wd.cwd), Configuration(), git.DEFAULT_DESCRIBE)


def sudo_devnull(
    args: list[str | os.PathLike[str]], check: bool = False
) -> subprocess.CompletedProcess[bytes]:
    """shortcut to run sudo with non-interactive input"""
    return subprocess.run(
        ["sudo", *args],
        stdin=subprocess.DEVNULL,
        check=check,
    )


@contextlib.contextmanager
def break_folder_permissions(path: Path) -> Generator[None, None, None]:
    """break the permissions of a folder for a while"""
    if not shutil.which("sudo"):
        pytest.skip("sudo executable not found")
    original_stat = path.stat()

    proc = sudo_devnull(["chown", "-R", "12345", path])
    if proc.returncode != 0:
        pytest.xfail("Failed to change ownership, is passwordless sudo available?")

    try:
        sudo_devnull(["chmod", "a+r", path], check=True)
        sudo_devnull(["chgrp", "-R", "12345", path], check=True)
        yield
    finally:
        # Restore the ownership
        sudo_devnull(["chown", "-R", str(original_stat.st_uid), path], check=True)
        sudo_devnull(["chgrp", "-R", str(original_stat.st_gid), path], check=True)


@pytest.mark.issue("https://github.com/pypa/setuptools-scm/issues/707")
def test_not_owner(wd: WorkDir) -> None:
    with break_folder_permissions(wd.cwd):
        assert git.parse(str(wd.cwd), Configuration())


def test_version_from_git(wd: WorkDir) -> None:
    assert wd.get_version() == "0.1.dev0+d20090213"

    parsed = git.parse(str(wd.cwd), Configuration(), git.DEFAULT_DESCRIBE)
    assert parsed is not None
    assert parsed.branch in ("master", "main")

    wd.commit_testfile()
    assert wd.get_version().startswith("0.1.dev1+g")
    assert not wd.get_version().endswith("1-")

    wd("git tag v0.1")
    assert wd.get_version() == "0.1"

    wd.write("test.txt", "test2")
    assert wd.get_version().startswith("0.2.dev0+g")

    wd.commit_testfile()
    assert wd.get_version().startswith("0.2.dev1+g")

    wd("git tag version-0.2")
    assert wd.get_version().startswith("0.2")

    wd.commit_testfile()
    wd("git tag version-0.2.post210+gbe48adfpost3+g0cc25f2")
    with pytest.warns(
        UserWarning, match="tag '.*' will be stripped of its suffix '.*'"
    ):
        assert wd.get_version().startswith("0.2")

    wd.commit_testfile()
    wd("git tag 17.33.0-rc")
    assert wd.get_version() == "17.33.0rc0"

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
    # monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")
    monkeypatch.chdir(wd.cwd)
    wd.write("setup.py", dedent(setup_py_txt))

    # do git operations and tag
    wd.commit_testfile()
    wd("git tag 17.33.0-rc1")

    # setuptools still normalizes using packaging.Version (removing the dash)
    res = wd([sys.executable, "setup.py", "--version"])
    assert res == "17.33.0rc1"

    # but the version tag in the file is non-normalized (with the dash)
    assert wd.cwd.joinpath("VERSION.txt").read_text(encoding="utf-8") == "17.33.0-rc1"


@pytest.mark.issue(179)
def test_unicode_version_scheme(wd: WorkDir) -> None:
    scheme = b"guess-next-dev".decode("ascii")
    assert wd.get_version(version_scheme=scheme)


@pytest.mark.issue(108)
@pytest.mark.issue(109)
def test_git_worktree(wd: WorkDir) -> None:
    wd.write("test.txt", "test2")
    # untracked files dont change the state
    assert wd.get_version() == "0.1.dev0+d20090213"

    wd("git add test.txt")
    assert wd.get_version().startswith("0.1.dev0+d")


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
    version = wd.get_version()

    if today:
        # the date on the tag is in UTC
        tag = datetime.now(timezone.utc).date().strftime(".d%Y%m%d")
    else:
        tag = ".d20090213"
    assert version.startswith("0.1.dev1+g")
    assert version.endswith(tag)


@pytest.mark.issue(193)
@pytest.mark.xfail(reason="sometimes relative path results")
def test_git_worktree_support(wd: WorkDir, tmp_path: Path) -> None:
    wd.commit_testfile()
    worktree = tmp_path / "work_tree"
    wd(f"git worktree add -b work-tree {worktree}")

    res = run([sys.executable, "-m", "setuptools_scm", "ls"], cwd=worktree)
    assert "test.txt" in res.stdout
    assert str(worktree) in res.stdout


@pytest.fixture
def shallow_wd(wd: WorkDir, tmp_path: Path) -> Path:
    wd.commit_testfile()
    wd.commit_testfile()
    wd.commit_testfile()
    target = tmp_path / "wd_shallow"
    run(["git", "clone", f"file://{wd.cwd}", target, "--depth=1"], tmp_path, check=True)
    return target


def test_git_parse_shallow_warns(
    shallow_wd: Path, recwarn: pytest.WarningsRecorder
) -> None:
    git.parse(shallow_wd, Configuration())
    print(list(recwarn))
    msg = recwarn.pop()
    assert "is shallow and may cause errors" in str(msg.message)


def test_git_parse_shallow_fail(shallow_wd: Path) -> None:
    with pytest.raises(ValueError, match="git fetch"):
        git.parse(str(shallow_wd), Configuration(), pre_parse=git.fail_on_shallow)


def test_git_shallow_autocorrect(
    shallow_wd: Path, recwarn: pytest.WarningsRecorder
) -> None:
    git.parse(str(shallow_wd), Configuration(), pre_parse=git.fetch_on_shallow)
    msg = recwarn.pop()
    assert "git fetch was used to rectify" in str(msg.message)
    git.parse(str(shallow_wd), Configuration(), pre_parse=git.fail_on_shallow)


def test_find_files_stop_at_root_git(wd: WorkDir) -> None:
    wd.commit_testfile()
    project = wd.cwd / "project"
    project.mkdir()
    project.joinpath("setup.cfg").touch()
    assert setuptools_scm._file_finders.find_files(str(project)) == []


@pytest.mark.issue(128)
def test_parse_no_worktree(tmp_path: Path) -> None:
    ret = git.parse(str(tmp_path), Configuration(root=str(tmp_path)))
    assert ret is None


def test_alphanumeric_tags_match(wd: WorkDir) -> None:
    wd.commit_testfile()
    wd("git tag newstyle-development-started")
    assert wd.get_version().startswith("0.1.dev1+g")


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
    assert setuptools_scm._file_finders.find_files(".") == [opj(".", "test1.txt")]


@pytest.mark.issue(228)
def test_git_archive_subdirectory(wd: WorkDir, monkeypatch: pytest.MonkeyPatch) -> None:
    os.mkdir(wd.cwd / "foobar")
    wd.write("foobar/test1.txt", "test")
    wd("git add foobar")
    wd.commit()
    monkeypatch.chdir(wd.cwd)
    assert setuptools_scm._file_finders.find_files(".") == [
        opj(".", "foobar", "test1.txt")
    ]


@pytest.mark.issue(251)
def test_git_archive_run_from_subdirectory(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    os.mkdir(wd.cwd / "foobar")
    wd.write("foobar/test1.txt", "test")
    wd("git add foobar")
    wd.commit()
    monkeypatch.chdir(wd.cwd / "foobar")
    assert setuptools_scm._file_finders.find_files(".") == [opj(".", "test1.txt")]


@pytest.mark.issue("https://github.com/pypa/setuptools-scm/issues/728")
def test_git_branch_names_correct(wd: WorkDir) -> None:
    wd.commit_testfile()
    wd("git checkout -b test/fun")
    wd_git = git.GitWorkdir(wd.cwd)
    assert wd_git.get_branch() == "test/fun"


def test_git_feature_branch_increments_major(wd: WorkDir) -> None:
    wd.commit_testfile()
    wd("git tag 1.0.0")
    wd.commit_testfile()
    assert wd.get_version(version_scheme="python-simplified-semver").startswith("1.0.1")
    wd("git checkout -b feature/fun")
    wd.commit_testfile()
    assert wd.get_version(version_scheme="python-simplified-semver").startswith("1.1.0")


@pytest.mark.issue("https://github.com/pypa/setuptools-scm/issues/303")
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


@pytest.mark.issue("https://github.com/pypa/setuptools-scm/issues/411")
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


@pytest.mark.issue("https://github.com/pypa/setuptools-scm/issues/381")
def test_gitdir(monkeypatch: pytest.MonkeyPatch, wd: WorkDir) -> None:
    """ """
    wd.commit_testfile()
    normal = wd.get_version()
    # git hooks set this and break subsequent setuptools-scm unless we clean
    monkeypatch.setenv("GIT_DIR", __file__)
    assert wd.get_version() == normal


def test_git_getdate(wd: WorkDir) -> None:
    # TODO: case coverage for git wd parse
    today = datetime.now(timezone.utc).date()

    def parse_date() -> date:
        parsed = git.parse(os.fspath(wd.cwd), Configuration())
        assert parsed is not None
        assert parsed.node_date is not None
        return parsed.node_date

    git_wd = git.GitWorkdir(wd.cwd)
    assert git_wd.get_head_date() is None
    assert parse_date() == today

    wd.commit_testfile()
    assert git_wd.get_head_date() == today
    assert parse_date() == today


def test_git_getdate_badgit(
    wd: WorkDir, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    wd.commit_testfile()
    git_wd = git.GitWorkdir(wd.cwd)
    fake_date_result = CompletedProcess(args=[], stdout="%cI", stderr="", returncode=0)
    with patch.object(
        git,
        "run_git",
        Mock(return_value=fake_date_result),
    ):
        assert git_wd.get_head_date() is None


def test_git_getdate_git_2_45_0_plus(
    wd: WorkDir, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    wd.commit_testfile()
    git_wd = git.GitWorkdir(wd.cwd)
    fake_date_result = CompletedProcess(
        args=[], stdout="2024-04-30T22:33:10Z", stderr="", returncode=0
    )
    with patch.object(
        git,
        "run_git",
        Mock(return_value=fake_date_result),
    ):
        assert git_wd.get_head_date() == date(2024, 4, 30)


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


@pytest.mark.issue("https://github.com/pypa/setuptools-scm/issues/548")
def test_git_getdate_signed_commit(signed_commit_wd: WorkDir) -> None:
    today = datetime.now(timezone.utc).date()
    signed_commit_wd.commit_testfile(signed=True)
    git_wd = git.GitWorkdir(signed_commit_wd.cwd)
    assert git_wd.get_head_date() == today


@pytest.mark.parametrize(
    ("expected", "from_data"),
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
        ("1.2.2", {"describe-name": "v1.2.2"}),
    ],
)
@pytest.mark.filterwarnings("ignore:git archive did not support describe output")
def test_git_archival_to_version(expected: str, from_data: dict[str, str]) -> None:
    config = Configuration(
        version_scheme="guess-next-dev", local_scheme="node-and-date"
    )
    version = archival_to_version(from_data, config=config)
    assert version is not None
    assert format_version(version) == expected


@pytest.mark.issue("https://github.com/pypa/setuptools-scm/issues/727")
def test_git_archival_node_missing_no_version() -> None:
    config = Configuration()
    version = archival_to_version({}, config=config)
    assert version is None


def test_git_archival_from_unfiltered() -> None:
    config = Configuration()

    with pytest.warns(
        UserWarning, match=r"unprocessed git archival found \(no export subst applied\)"
    ):
        version = archival_to_version({"node": "$Format:%H$"}, config=config)
    assert version is None
