"""Setuptools-scm specific regression tests.

Core VCS regression tests have been moved to vcs-versioning/testing_vcs/test_regressions.py
"""

from __future__ import annotations

import pprint
import subprocess
import sys

from importlib.metadata import EntryPoint
from importlib.metadata import distribution
from pathlib import Path

import pytest

from vcs_versioning._run_cmd import run
from vcs_versioning.test_api import WorkDir

from setuptools_scm.integration import data_from_mime


def test_data_from_mime_ignores_body() -> None:
    assert data_from_mime(
        "test",
        "version: 1.0\r\n\r\nversion: bad",
    ) == {"version": "1.0"}


def test_pkginfo_noscmroot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """if we are indeed a sdist, the root does not apply"""
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")

    # we should get the version from pkg-info if git is broken
    p = tmp_path.joinpath("sub/package")
    p.mkdir(parents=True)

    tmp_path.joinpath(".git").mkdir()
    p.joinpath("setup.py").write_text(
        """\
from setuptools import setup
setup(use_scm_version={"root": ".."})
""",
        encoding="utf-8",
    )

    res = run([sys.executable, "setup.py", "--version"], p)
    assert "setuptools-scm was unable to detect version for" in res.stderr
    assert res.returncode == 1

    p.joinpath("PKG-INFO").write_text("Version: 1.0", encoding="utf-8")
    res = run([sys.executable, "setup.py", "--version"], p)
    assert res.stdout == "1.0"

    try:
        run("git init", p.parent)
    except OSError:
        pass
    else:
        res = run([sys.executable, "setup.py", "--version"], p)
        assert res.stdout == "0.1.dev0+d20090213"


@pytest.mark.issue(164)
def test_pip_download(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    subprocess.check_call([sys.executable, "-m", "pip", "download", "lz4==0.9.0"])


def test_use_scm_version_callable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """use of callable as use_scm_version argument"""
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")

    p = tmp_path / "sub" / "package"
    p.mkdir(parents=True)
    p.joinpath("setup.py").write_text(
        """from setuptools import setup
def vcfg():
    from setuptools_scm.version import guess_next_dev_version
    def vs(v):
        return guess_next_dev_version(v)
    return {"version_scheme": vs}
setup(use_scm_version=vcfg)
""",
        encoding="utf-8",
    )
    p.joinpath("PKG-INFO").write_text("Version: 1.0", encoding="utf-8")

    res = run([sys.executable, "setup.py", "--version"], p)
    assert res.stdout == "1.0"


def test_case_mismatch_force_assertion_failure(tmp_path: Path) -> None:
    """Force the assertion failure by directly calling _git_toplevel with mismatched paths"""

    from vcs_versioning._file_finders._git import _git_toplevel

    # Create git repo structure
    repo_path = tmp_path / "my_repo"
    repo_path.mkdir()
    wd = WorkDir(repo_path).setup_git()

    # Create nested directory
    nested_dir = repo_path / "CasedDir"
    nested_dir.mkdir()

    # Add and commit something to make it a valid repo
    wd.write("CasedDir/test.txt", "test")
    wd.add_and_commit("Initial commit")

    # Now call _git_toplevel with a path that has different casing
    # This should cause the assertion to fail
    lowercase_nested_path = str(nested_dir).replace("CasedDir", "caseddir")

    try:
        result = _git_toplevel(lowercase_nested_path)
        print(f"_git_toplevel returned: {result}")
        # If no assertion error, either the bug is fixed or we didn't trigger it properly
    except AssertionError as e:
        print(f"AssertionError as expected: {e}")
        raise  # Let the test fail to show we reproduced the issue


def test_entrypoints_load() -> None:
    d = distribution("setuptools-scm")

    eps = d.entry_points
    failed: list[tuple[EntryPoint, Exception]] = []
    for ep in eps:
        try:
            ep.load()
        except Exception as e:
            failed.append((ep, e))
    if failed:
        pytest.fail(pprint.pformat(failed))
