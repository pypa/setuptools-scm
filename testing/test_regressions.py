from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from setuptools_scm import get_version
from setuptools_scm.git import parse
from setuptools_scm.utils import do
from setuptools_scm.utils import do_ex


def test_pkginfo_noscmroot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """if we are indeed a sdist, the root does not apply"""
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")

    # we should get the version from pkg-info if git is broken
    p = tmp_path.joinpath("sub/package")
    p.mkdir(parents=True)

    tmp_path.joinpath(".git").mkdir()
    p.joinpath("setup.py").write_text(
        "from setuptools import setup;" 'setup(use_scm_version={"root": ".."})'
    )

    _, stderr, ret = do_ex([sys.executable, "setup.py", "--version"], p)
    assert "setuptools-scm was unable to detect version for" in stderr
    assert ret == 1

    p.joinpath("PKG-INFO").write_text("Version: 1.0")
    res = do([sys.executable, "setup.py", "--version"], p)
    assert res == "1.0"

    try:
        do("git init", p.parent)
    except OSError:
        pass
    else:
        res = do([sys.executable, "setup.py", "--version"], p)
        assert res == "0.1.dev0"


def test_pip_egg_info(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """if we are indeed a sdist, the root does not apply"""

    # we should get the version from pkg-info if git is broken
    p = tmp_path.joinpath("sub/package")
    p.mkdir(parents=True)
    tmp_path.joinpath(".git").mkdir()
    p.joinpath("setup.py").write_text(
        "from setuptools import setup;" 'setup(use_scm_version={"root": ".."})'
    )

    with pytest.raises(LookupError):
        get_version(root=os.fspath(p), fallback_root=os.fspath(p))

    bad_egg_info = p.joinpath("pip-egg-info/random.egg-info/")
    bad_egg_info.mkdir(parents=True)

    bad_egg_info.joinpath("PKG-INFO").write_text("Version: 1.0")
    assert get_version(root=os.fspath(p), fallback_root=os.fspath(p)) == "1.0"


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
"""
    )
    p.joinpath("PKG-INFO").write_text("Version: 1.0")

    res = do([sys.executable, "setup.py", "--version"], p)
    assert res == "1.0"


@pytest.mark.skipif(sys.platform != "win32", reason="this bug is only valid on windows")
def test_case_mismatch_on_windows_git(tmp_path: Path) -> None:
    """Case insensitive path checks on Windows"""
    camel_case_path = tmp_path / "CapitalizedDir"
    camel_case_path.mkdir()
    do("git init", camel_case_path)
    res = parse(str(camel_case_path).lower())
    assert res is not None
