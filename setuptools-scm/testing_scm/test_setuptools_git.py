"""Tests for setuptools_scm integration with git via setup.py use_scm_version.

These tests require setuptools_scm to be installed because they exercise the
distutils.setup_keywords hook (use_scm_version).

Moved from vcs-versioning/testing_vcs/test_git.py as part of #1353.
"""

from __future__ import annotations

import sys

from pathlib import Path
from textwrap import dedent

import pytest

from vcs_versioning._run_cmd import run
from vcs_versioning.test_api import WorkDir


@pytest.fixture
def wd(wd: WorkDir, monkeypatch: pytest.MonkeyPatch) -> WorkDir:
    """Set up git for setuptools integration tests."""
    wd.setup_git(monkeypatch)
    return wd


def test_root_relative_to(wd: WorkDir, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG", raising=False)
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
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG", raising=False)
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

    @property
    def public(self):
        return self.version.split('+')[0]

    @property
    def local(self):
        if '+' in self.version:
            return self.version.split('+', 1)[1]
        return None

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
    monkeypatch.setenv("SETUPTOOLS_SCM_WRITE_TO_SOURCE", "1")
    monkeypatch.chdir(wd.cwd)
    wd.write("setup.py", dedent(setup_py_txt))

    wd.commit_testfile()
    wd("git tag 17.33.0-rc1")

    res = wd([sys.executable, "setup.py", "--version"])
    assert res == "17.33.0rc1"

    assert wd.cwd.joinpath("VERSION.txt").read_text(encoding="utf-8") == "17.33.0-rc1"


@pytest.mark.issue(193)
@pytest.mark.xfail(reason="sometimes relative path results")
def test_git_worktree_support(wd: WorkDir, tmp_path: Path) -> None:

    wd.commit_testfile()
    worktree = tmp_path / "work_tree"
    wd(f"git worktree add -b work-tree {worktree}")

    res = run([sys.executable, "-m", "setuptools_scm", "ls"], cwd=worktree)
    assert "test.txt" in res.stdout
    assert str(worktree) in res.stdout
