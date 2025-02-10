from __future__ import annotations

import os
import sys

from typing import Iterable

import pytest

from setuptools_scm._file_finders import find_files

from .wd_wrapper import WorkDir


@pytest.fixture(params=["git", "hg"])
def inwd(
    request: pytest.FixtureRequest, wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> WorkDir:
    param: str = request.param  # type: ignore
    if param == "git":
        try:
            wd("git init")
        except OSError:
            pytest.skip("git executable not found")
        wd("git config user.email test@example.com")
        wd('git config user.name "a test"')
        wd.add_command = "git add ."
        wd.commit_command = "git commit -m test-{reason}"
    elif param == "hg":
        try:
            wd("hg init")
        except OSError:
            pytest.skip("hg executable not found")
        wd.add_command = "hg add ."
        wd.commit_command = 'hg commit -m test-{reason} -u test -d "0 0"'
    (wd.cwd / "file1").touch()
    adir = wd.cwd / "adir"
    adir.mkdir()
    (adir / "filea").touch()
    bdir = wd.cwd / "bdir"
    bdir.mkdir()
    (bdir / "fileb").touch()
    if request.node.get_closest_marker("skip_commit") is None:
        wd.add_and_commit()
    monkeypatch.chdir(wd.cwd)
    return wd


def _sep(paths: Iterable[str]) -> set[str]:
    return {path.replace("/", os.path.sep) for path in paths}


def test_basic(inwd: WorkDir) -> None:
    assert set(find_files()) == _sep({"file1", "adir/filea", "bdir/fileb"})
    assert set(find_files(".")) == _sep({"./file1", "./adir/filea", "./bdir/fileb"})
    assert set(find_files("adir")) == _sep({"adir/filea"})


def test_whitespace(inwd: WorkDir) -> None:
    (inwd.cwd / "adir" / "space file").touch()
    inwd.add_and_commit()
    assert set(find_files("adir")) == _sep({"adir/space file", "adir/filea"})


def test_case(inwd: WorkDir) -> None:
    (inwd.cwd / "CamelFile").touch()
    (inwd.cwd / "file2").touch()
    inwd.add_and_commit()
    assert set(find_files()) == _sep(
        {"CamelFile", "file2", "file1", "adir/filea", "bdir/fileb"}
    )


@pytest.mark.skipif(
    os.path.normcase("B") != os.path.normcase("b"), reason="case sensitive filesystem"
)
def test_case_cwd_evil(inwd: WorkDir, monkeypatch: pytest.MonkeyPatch) -> None:
    (inwd.cwd / "CamelFile").touch()
    (inwd.cwd / "file2").touch()
    inwd.add_and_commit()
    monkeypatch.chdir(inwd.cwd.parent.joinpath(inwd.cwd.name.capitalize()))
    assert set(find_files()) == _sep(
        {"CamelFile", "file2", "file1", "adir/filea", "bdir/fileb"}
    )


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks to dir not supported")
def test_symlink_dir(inwd: WorkDir) -> None:
    (inwd.cwd / "adir" / "bdirlink").symlink_to("../bdir")
    inwd.add_and_commit()
    assert set(find_files("adir")) == _sep({"adir/filea", "adir/bdirlink/fileb"})


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks to dir not supported")
def test_symlink_dir_source_not_in_scm(inwd: WorkDir) -> None:
    (inwd.cwd / "adir" / "bdirlink").symlink_to("../bdir")
    assert set(find_files("adir")) == _sep({"adir/filea"})


@pytest.mark.skipif(
    sys.platform == "win32", reason="symlinks to files not supported on windows"
)
def test_symlink_file(inwd: WorkDir) -> None:
    (inwd.cwd / "adir" / "file1link").symlink_to("../file1")
    inwd.add_and_commit()
    assert set(find_files("adir")) == _sep(
        {"adir/filea", "adir/file1link"}
    )  # -> ../file1


@pytest.mark.skipif(
    sys.platform == "win32", reason="symlinks to files not supported on windows"
)
def test_symlink_file_source_not_in_scm(inwd: WorkDir) -> None:
    (inwd.cwd / "adir" / "file1link").symlink_to("../file1")
    assert set(find_files("adir")) == _sep({"adir/filea"})


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks to dir not supported")
def test_symlink_loop(inwd: WorkDir) -> None:
    (inwd.cwd / "adir" / "loop").symlink_to("../adir")
    inwd.add_and_commit()
    assert set(find_files("adir")) == _sep({"adir/filea", "adir/loop"})  # -> ../adir


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks to dir not supported")
def test_symlink_loop_outside_path(inwd: WorkDir) -> None:
    (inwd.cwd / "bdir" / "loop").symlink_to("../bdir")
    (inwd.cwd / "adir" / "bdirlink").symlink_to("../bdir")
    inwd.add_and_commit()
    assert set(find_files("adir")) == _sep({"adir/filea", "adir/bdirlink/fileb"})


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks to dir not supported")
def test_symlink_dir_out_of_git(inwd: WorkDir) -> None:
    (inwd.cwd / "adir" / "outsidedirlink").symlink_to(os.path.join(__file__, ".."))
    inwd.add_and_commit()
    assert set(find_files("adir")) == _sep({"adir/filea"})


@pytest.mark.skipif(
    sys.platform == "win32", reason="symlinks to files not supported on windows"
)
def test_symlink_file_out_of_git(inwd: WorkDir) -> None:
    (inwd.cwd / "adir" / "outsidefilelink").symlink_to(__file__)
    inwd.add_and_commit()
    assert set(find_files("adir")) == _sep({"adir/filea"})


@pytest.mark.parametrize("path_add", ["{cwd}", "{cwd}" + os.pathsep + "broken"])
def test_ignore_root(
    inwd: WorkDir, monkeypatch: pytest.MonkeyPatch, path_add: str
) -> None:
    monkeypatch.setenv("SETUPTOOLS_SCM_IGNORE_VCS_ROOTS", path_add.format(cwd=inwd.cwd))
    assert find_files() == []


def test_empty_root(inwd: WorkDir) -> None:
    subdir = inwd.cwd / "cdir" / "subdir"
    subdir.mkdir(parents=True)
    (subdir / "filec").touch()
    inwd.add_and_commit()
    assert set(find_files("cdir")) == _sep({"cdir/subdir/filec"})


def test_empty_subdir(inwd: WorkDir) -> None:
    subdir = inwd.cwd / "adir" / "emptysubdir" / "subdir"
    subdir.mkdir(parents=True)
    (subdir / "xfile").touch()
    inwd.add_and_commit()
    assert set(find_files("adir")) == _sep(
        {"adir/filea", "adir/emptysubdir/subdir/xfile"}
    )


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks not supported on windows")
def test_double_include_through_symlink(inwd: WorkDir) -> None:
    (inwd.cwd / "data").mkdir()
    (inwd.cwd / "data" / "datafile").touch()
    (inwd.cwd / "adir" / "datalink").symlink_to("../data")
    (inwd.cwd / "adir" / "filealink").symlink_to("filea")
    inwd.add_and_commit()
    assert set(find_files()) == _sep(
        {
            "file1",
            "adir/datalink",  # -> ../data
            "adir/filealink",  # -> filea
            "adir/filea",
            "bdir/fileb",
            "data/datafile",
        }
    )


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks not supported on windows")
def test_symlink_not_in_scm_while_target_is(inwd: WorkDir) -> None:
    (inwd.cwd / "data").mkdir()
    (inwd.cwd / "data" / "datafile").touch()
    inwd.add_and_commit()
    (inwd.cwd / "adir" / "datalink").symlink_to("../data")
    (inwd.cwd / "adir" / "filealink").symlink_to("filea")
    assert set(find_files()) == _sep(
        {
            "file1",
            "adir/filea",
            # adir/datalink and adir/afilelink not included
            # because the symlink_to themselves are not in scm
            "bdir/fileb",
            "data/datafile",
        }
    )


@pytest.mark.issue(587)
@pytest.mark.skip_commit
def test_not_commited(inwd: WorkDir) -> None:
    assert find_files() == []


def test_unexpanded_git_archival(wd: WorkDir, monkeypatch: pytest.MonkeyPatch) -> None:
    # When substitutions in `.git_archival.txt` are not expanded, files should
    # not be automatically listed.
    monkeypatch.chdir(wd.cwd)
    (wd.cwd / ".git_archival.txt").write_text("node: $Format:%H$", encoding="utf-8")
    (wd.cwd / "file1.txt").touch()
    assert find_files() == []


@pytest.mark.parametrize("archive_file", [".git_archival.txt", ".hg_archival.txt"])
def test_archive(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch, archive_file: str
) -> None:
    # When substitutions in `.git_archival.txt` are not expanded, files should
    # not be automatically listed.
    monkeypatch.chdir(wd.cwd)
    sha = "a1bda3d984d1a40d7b00ae1d0869354d6d503001"
    (wd.cwd / archive_file).write_text(f"node: {sha}", encoding="utf-8")
    (wd.cwd / "data").mkdir()
    (wd.cwd / "data" / "datafile").touch()

    datalink = wd.cwd / "data" / "datalink"
    if sys.platform != "win32":
        datalink.symlink_to("data/datafile")
    else:
        os.link("data/datafile", datalink)

    assert set(find_files()) == _sep({archive_file, "data/datafile", "data/datalink"})
