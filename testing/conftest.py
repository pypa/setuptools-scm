from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

import setuptools_scm.utils
from .wd_wrapper import WorkDir


def pytest_configure() -> None:
    # 2009-02-13T23:31:30+00:00
    os.environ["SOURCE_DATE_EPOCH"] = "1234567890"
    os.environ["SETUPTOOLS_SCM_DEBUG"] = "1"


VERSION_PKGS = ["setuptools", "setuptools_scm", "packaging"]


def pytest_report_header() -> list[str]:
    try:
        from importlib.metadata import version  # type: ignore
    except ImportError:
        from importlib_metadata import version  # type: ignore
    res = []
    for pkg in VERSION_PKGS:
        pkg_version = version(pkg)
        path = __import__(pkg).__file__
        res.append(f"{pkg} version {pkg_version} from {path!r}")
    return res


def pytest_addoption(parser: Any) -> None:
    group = parser.getgroup("setuptools_scm")
    group.addoption(
        "--test-legacy", dest="scm_test_virtualenv", default=False, action="store_true"
    )


class DebugMode:
    def __init__(self, monkeypatch: pytest.MonkeyPatch):
        self.__monkeypatch = monkeypatch
        self.__module = setuptools_scm.utils

    __monkeypatch: pytest.MonkeyPatch

    def enable(self) -> None:
        self.__monkeypatch.setattr(self.__module, "DEBUG", True)

    def disable(self) -> None:
        self.__monkeypatch.setattr(self.__module, "DEBUG", False)


@pytest.fixture(autouse=True)
def debug_mode(monkeypatch: pytest.MonkeyPatch) -> DebugMode:
    debug_mode = DebugMode(monkeypatch)
    debug_mode.enable()
    return debug_mode


@pytest.fixture
def wd(tmp_path: Path) -> WorkDir:
    target_wd = tmp_path.resolve() / "wd"
    target_wd.mkdir()
    return WorkDir(target_wd)


@pytest.fixture
def repositories_hg_git(tmp_path: Path) -> tuple[WorkDir, WorkDir]:
    from setuptools_scm.utils import do

    tmp_path = tmp_path.resolve()
    path_git = tmp_path / "repo_git"
    path_git.mkdir()

    wd = WorkDir(path_git)
    wd("git init")
    wd("git config user.email test@example.com")
    wd('git config user.name "a test"')
    wd.add_command = "git add ."
    wd.commit_command = "git commit -m test-{reason}"

    path_hg = tmp_path / "repo_hg"
    do(f"hg clone {path_git} {path_hg} --config extensions.hggit=")
    assert path_hg.exists()

    with open(path_hg / ".hg/hgrc", "a") as file:
        file.write("[extensions]\nhggit =\n")

    wd_hg = WorkDir(path_hg)
    wd_hg.add_command = "hg add ."
    wd_hg.commit_command = 'hg commit -m test-{reason} -u test -d "0 0"'

    return wd_hg, wd
