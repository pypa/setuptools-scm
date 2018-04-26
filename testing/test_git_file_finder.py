import os
import sys

import pytest

from setuptools_scm.git_file_finder import find_files


@pytest.fixture
def inwd(wd):
    wd('git init')
    wd('git config user.email test@example.com')
    wd('git config user.name "a test"')
    wd.add_command = 'git add .'
    wd.commit_command = 'git commit -m test-{reason}'
    (wd.cwd / 'file1').ensure(file=True)
    adir = (wd.cwd / 'adir').ensure(dir=True)
    (adir / 'filea').ensure(file=True)
    bdir = (wd.cwd / 'bdir').ensure(dir=True)
    (bdir / 'fileb').ensure(file=True)
    wd.add_and_commit()
    with wd.cwd.as_cwd():
        yield wd


def test_basic(inwd):
    assert set(find_files()) == {
        'file1',
        'adir/filea',
        'bdir/fileb',
    }
    assert set(find_files('.')) == {
        './file1',
        './adir/filea',
        './bdir/fileb',
    }
    assert set(find_files('adir')) == {
        'adir/filea',
    }


@pytest.mark.skipif(sys.platform == 'win32',
                    reason="symlinks to dir not supported")
def test_symlink_dir(inwd):
    (inwd.cwd / 'adir' / 'bdirlink').mksymlinkto('../bdir')
    inwd.add_and_commit()
    assert set(find_files('adir')) == {
        'adir/filea',
        'adir/bdirlink/fileb',
    }


@pytest.mark.skipif(sys.platform == 'win32',
                    reason="symlinks to files not supported on windows")
def test_symlink_file(inwd):
    (inwd.cwd / 'adir' / 'file1link').mksymlinkto('../file1')
    inwd.add_and_commit()
    assert set(find_files('adir')) == {
        'adir/filea',
        'adir/file1link',
    }


@pytest.mark.skipif(sys.platform == 'win32',
                    reason="symlinks to dir not supported")
def test_symlink_loop(inwd):
    (inwd.cwd / 'adir' / 'loop').mksymlinkto('../adir')
    inwd.add_and_commit()
    assert set(find_files('adir')) == {
        'adir/filea',
    }


@pytest.mark.skipif(sys.platform == 'win32',
                    reason="symlinks to dir not supported")
def test_symlink_dir_out_of_git(inwd):
    (inwd.cwd / 'adir' / 'outsidedirlink').\
        mksymlinkto(os.path.join(__file__, '..'))
    inwd.add_and_commit()
    assert set(find_files('adir')) == {
        'adir/filea',
    }


@pytest.mark.skipif(sys.platform == 'win32',
                    reason="symlinks to files not supported on windows")
def test_symlink_file_out_of_git(inwd):
    (inwd.cwd / 'adir' / 'outsidefilelink').mksymlinkto(__file__)
    inwd.add_and_commit()
    assert set(find_files('adir')) == {
        'adir/filea',
    }


def test_empty_root(inwd):
    subdir = inwd.cwd / 'cdir' / 'subdir'
    subdir.ensure(dir=True)
    (subdir / 'filec').ensure(file=True)
    inwd.add_and_commit()
    assert set(find_files('cdir')) == {
        'cdir/subdir/filec',
    }


def test_empty_subdir(inwd):
    subdir = inwd.cwd / 'adir' / 'emptysubdir' / 'subdir'
    subdir.ensure(dir=True)
    (subdir / 'xfile').ensure(file=True)
    inwd.add_and_commit()
    assert set(find_files('adir')) == {
        'adir/filea',
        'adir/emptysubdir/subdir/xfile',
    }
