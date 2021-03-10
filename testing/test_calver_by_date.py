import sys
from datetime import date, timedelta

from setuptools_scm import integration
from setuptools_scm.utils import do, has_command
from setuptools_scm import git
import pytest
from datetime import datetime
from os.path import join as opj
from setuptools_scm.file_finder_git import git_find_files


SCRIPT = u"""
#!/usr/bin/env python


from setuptools import setup


def calver_by_date():
    from setuptools_scm.version import guess_next_version, format_version, trace
    def version_scheme(version):
        version_ = version.branch  # FIXME set to None
        if version.branch.startswith('release-'):
            trace('in release branch')
            version_ = version.branch.replace('relese-', '')
        elif version.dirty:
            # get next release
            trace('in dirty')
            version_ = guess_next_version(version.tag)
        elif version.exact:
            trace('in exact')
            version_ = version.format_with("{tag}")
        else:
            trace('in default fallback')
            version_ = format_version(version, version_scheme=None, local_scheme=None)
        return version_   
        
    return {'version_scheme': version_scheme}

setup(use_scm_version=calver_by_date)

"""


def add_test_file(working_dir):
    working_dir.write('test.txt', 'hi test file')


def date_to_str(date_, days_offset=0):
    date_ = date_ - timedelta(days=days_offset)
    return date_.strftime("%y.%-m.%-d")


@pytest.fixture
def today(days_offset=0):
    date_ = date.today()
    return date_to_str(date_)


@pytest.fixture
def wd(wd, monkeypatch):
    monkeypatch.delenv("HOME", raising=False)
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")
    wd("git init")
    wd("git config user.email test@example.com")
    wd('git config user.name "a test"')
    wd.write("setup.py", SCRIPT)
    wd("git add .")
    wd("git commit -a -m test-{reason}")
    return wd


def test_seq_clean(wd):
    wd("git tag 0.1")
    res = do((sys.executable, "setup.py", "--version"), wd.cwd)
    assert res == "0.1"


def test_date_clean(wd, today):
    wd(f"git tag {today}")
    res = do((sys.executable, "setup.py", "--version"), wd.cwd)
    assert res == today


def test_seq_uncommited(wd):
    wd("git tag 0.1")
    add_test_file(wd)
    res = do((sys.executable, "setup.py", "--version"), wd.cwd)
    assert res == "0.2"


def test_date_uncommited(wd, today):
    wd(f"git tag {today}")
    add_test_file(wd)
    res = do((sys.executable, "setup.py", "--version"), wd.cwd)
    assert res == "0.2"