# -*- coding: utf-8 -*-
# Copyright © 2018 ACSONE SA/NV
# License LGPLv3 (http://www.gnu.org/licenses/lgpl-3.0-standalone.html)

import os
import subprocess
import sys

from pathlib2 import Path
import pytest

from setuptools_scm.git_file_finder import find_files


@pytest.fixture
def ingitdir(tmpdir):
    cwd = os.getcwd()
    os.chdir(str(tmpdir))
    try:
        subprocess.check_call(['git', 'init'])
        Path('file1').touch()
        adir = Path('adir')
        adir.mkdir()
        (adir / 'filea').touch()
        bdir = Path('bdir')
        bdir.mkdir()
        (bdir / 'fileb').touch()
        subprocess.check_call(['git', 'add', '.'])
        subprocess.check_call(['git', 'commit', '-m', '...'])
        yield
    finally:
        os.chdir(cwd)


def test_basic(ingitdir):
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


def test_symlink_dir(ingitdir):
    (Path('adir') / 'bdirlink').\
        symlink_to('../bdir', target_is_directory=True)
    subprocess.check_call(['git', 'add', '.'])
    subprocess.check_call(['git', 'commit', '-m', '...'])
    assert set(find_files('adir')) == {
        'adir/filea',
        'adir/bdirlink/fileb',
    }


@pytest.mark.skipif(sys.platform == 'win32',
                    reason="symlinks to files not supported on windows")
def test_symlink_file(ingitdir):
    (Path('adir') / 'file1link').\
        symlink_to('../file1', target_is_directory=False)
    subprocess.check_call(['git', 'add', '.'])
    subprocess.check_call(['git', 'commit', '-m', '...'])
    assert set(find_files('adir')) == {
        'adir/filea',
        'adir/file1link',
    }


def test_symlink_loop(ingitdir):
    (Path('adir') / 'loop').\
        symlink_to('../adir', target_is_directory=True)
    subprocess.check_call(['git', 'add', '.'])
    subprocess.check_call(['git', 'commit', '-m', '...'])
    assert set(find_files('adir')) == {
        'adir/filea',
    }


def test_symlink_dir_out_of_git(ingitdir):
    (Path('adir') / 'outsidedirlink').\
        symlink_to(Path(__file__) / '..', target_is_directory=True)
    subprocess.check_call(['git', 'add', '.'])
    subprocess.check_call(['git', 'commit', '-m', '...'])
    assert set(find_files('adir')) == {
        'adir/filea',
    }


@pytest.mark.skipif(sys.platform == 'win32',
                    reason="symlinks to files not supported on windows")
def test_symlink_file_out_of_git(ingitdir):
    (Path('adir') / 'outsidefilelink').\
        symlink_to(__file__, target_is_directory=False)
    subprocess.check_call(['git', 'add', '.'])
    subprocess.check_call(['git', 'commit', '-m', '...'])
    assert set(find_files('adir')) == {
        'adir/filea',
    }


def test_empty_root(ingitdir):
    subdir = Path('cdir') / 'subdir'
    subdir.mkdir(parents=True)
    (subdir / 'filec').touch()
    subprocess.check_call(['git', 'add', '.'])
    subprocess.check_call(['git', 'commit', '-m', '...'])
    assert set(find_files('cdir')) == {
        'cdir/subdir/filec',
    }


def test_empty_subdir(ingitdir):
    subdir = Path('adir') / 'emptysubdir' / 'subdir'
    subdir.mkdir(parents=True)
    (subdir / 'xfile').touch()
    subprocess.check_call(['git', 'add', '.'])
    subprocess.check_call(['git', 'commit', '-m', '...'])
    assert set(find_files('adir')) == {
        'adir/filea',
        'adir/emptysubdir/subdir/xfile',
    }
