import os
import sys

import pytest

from setuptools_scm.integration import find_files


@pytest.fixture(params=["git", "hg"])
def inwd(request, wd):
    if request.param == "git":
        wd("git init")
        wd("git config user.email test@example.com")
        wd('git config user.name "a test"')
        wd.add_command = "git add ."
        wd.commit_command = "git commit -m test-{reason}"
    elif request.param == "hg":
        wd("hg init")
        wd.add_command = "hg add ."
        wd.commit_command = 'hg commit -m test-{reason} -u test -d "0 0"'
    (wd.cwd / "file1").ensure(file=True)
    adir = (wd.cwd / "adir").ensure(dir=True)
    (adir / "filea").ensure(file=True)
    bdir = (wd.cwd / "bdir").ensure(dir=True)
    (bdir / "fileb").ensure(file=True)
    wd.add_and_commit()
    with wd.cwd.as_cwd():
        yield wd


def _sep(paths):
    return {path.replace("/", os.path.sep) for path in paths}


def test_basic(inwd):
    assert set(find_files()) == _sep({"file1", "adir/filea", "bdir/fileb"})
    assert set(find_files(".")) == _sep({"./file1", "./adir/filea", "./bdir/fileb"})
    assert set(find_files("adir")) == _sep({"adir/filea"})


def test_whitespace(inwd):
    (inwd.cwd / "adir" / "space file").ensure(file=True)
    inwd.add_and_commit()
    assert set(find_files("adir")) == _sep({"adir/space file", "adir/filea"})


def test_case(inwd):
    (inwd.cwd / "CamelFile").ensure(file=True)
    (inwd.cwd / "file2").ensure(file=True)
    inwd.add_and_commit()
    assert (
        set(find_files())
        == _sep({"CamelFile", "file2", "file1", "adir/filea", "bdir/fileb"})
    )


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks to dir not supported")
def test_symlink_dir(inwd):
    (inwd.cwd / "adir" / "bdirlink").mksymlinkto("../bdir")
    inwd.add_and_commit()
    assert set(find_files("adir")) == _sep({"adir/filea", "adir/bdirlink/fileb"})


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks to dir not supported")
def test_symlink_dir_source_not_in_scm(inwd):
    (inwd.cwd / "adir" / "bdirlink").mksymlinkto("../bdir")
    assert set(find_files("adir")) == _sep({"adir/filea"})


@pytest.mark.skipif(
    sys.platform == "win32", reason="symlinks to files not supported on windows"
)
def test_symlink_file(inwd):
    (inwd.cwd / "adir" / "file1link").mksymlinkto("../file1")
    inwd.add_and_commit()
    assert (
        set(find_files("adir")) == _sep({"adir/filea", "adir/file1link"})  # -> ../file1
    )


@pytest.mark.skipif(
    sys.platform == "win32", reason="symlinks to files not supported on windows"
)
def test_symlink_file_source_not_in_scm(inwd):
    (inwd.cwd / "adir" / "file1link").mksymlinkto("../file1")
    assert set(find_files("adir")) == _sep({"adir/filea"})


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks to dir not supported")
def test_symlink_loop(inwd):
    (inwd.cwd / "adir" / "loop").mksymlinkto("../adir")
    inwd.add_and_commit()
    assert set(find_files("adir")) == _sep({"adir/filea", "adir/loop"})  # -> ../adir


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks to dir not supported")
def test_symlink_loop_outside_path(inwd):
    (inwd.cwd / "bdir" / "loop").mksymlinkto("../bdir")
    (inwd.cwd / "adir" / "bdirlink").mksymlinkto("../bdir")
    inwd.add_and_commit()
    assert set(find_files("adir")) == _sep({"adir/filea", "adir/bdirlink/fileb"})


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks to dir not supported")
def test_symlink_dir_out_of_git(inwd):
    (inwd.cwd / "adir" / "outsidedirlink").mksymlinkto(os.path.join(__file__, ".."))
    inwd.add_and_commit()
    assert set(find_files("adir")) == _sep({"adir/filea"})


@pytest.mark.skipif(
    sys.platform == "win32", reason="symlinks to files not supported on windows"
)
def test_symlink_file_out_of_git(inwd):
    (inwd.cwd / "adir" / "outsidefilelink").mksymlinkto(__file__)
    inwd.add_and_commit()
    assert set(find_files("adir")) == _sep({"adir/filea"})


def test_empty_root(inwd):
    subdir = inwd.cwd / "cdir" / "subdir"
    subdir.ensure(dir=True)
    (subdir / "filec").ensure(file=True)
    inwd.add_and_commit()
    assert set(find_files("cdir")) == _sep({"cdir/subdir/filec"})


def test_empty_subdir(inwd):
    subdir = inwd.cwd / "adir" / "emptysubdir" / "subdir"
    subdir.ensure(dir=True)
    (subdir / "xfile").ensure(file=True)
    inwd.add_and_commit()
    assert (
        set(find_files("adir")) == _sep({"adir/filea", "adir/emptysubdir/subdir/xfile"})
    )


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks not supported on windows")
def test_double_include_through_symlink(inwd):
    (inwd.cwd / "data").ensure(dir=True)
    (inwd.cwd / "data" / "datafile").ensure(file=True)
    (inwd.cwd / "adir" / "datalink").mksymlinkto("../data")
    (inwd.cwd / "adir" / "filealink").mksymlinkto("filea")
    inwd.add_and_commit()
    assert (
        set(find_files())
        == _sep(
            {
                "file1",
                "adir/datalink",  # -> ../data
                "adir/filealink",  # -> filea
                "adir/filea",
                "bdir/fileb",
                "data/datafile",
            }
        )
    )


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks not supported on windows")
def test_symlink_not_in_scm_while_target_is(inwd):
    (inwd.cwd / "data").ensure(dir=True)
    (inwd.cwd / "data" / "datafile").ensure(file=True)
    inwd.add_and_commit()
    (inwd.cwd / "adir" / "datalink").mksymlinkto("../data")
    (inwd.cwd / "adir" / "filealink").mksymlinkto("filea")
    assert (
        set(find_files())
        == _sep(
            {
                "file1",
                "adir/filea",
                # adir/datalink and adir/afilelink not included
                # because the symlink themselves are not in scm
                "bdir/fileb",
                "data/datafile",
            }
        )
    )
