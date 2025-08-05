from __future__ import annotations

import contextlib
import os
import shutil
import sys

from pathlib import Path
from types import TracebackType
from typing import Any
from typing import Iterator

import pytest

from setuptools_scm._run_cmd import run

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from .wd_wrapper import WorkDir


def pytest_configure(config: pytest.Config) -> None:
    # 2009-02-13T23:31:30+00:00
    os.environ["SOURCE_DATE_EPOCH"] = "1234567890"
    os.environ["SETUPTOOLS_SCM_DEBUG"] = "1"

    # Register custom markers
    config.addinivalue_line(
        "markers",
        "git: mark test to use git SCM",
    )
    config.addinivalue_line(
        "markers",
        "hg: mark test to use mercurial SCM",
    )


VERSION_PKGS = ["setuptools", "setuptools_scm", "packaging", "build", "wheel"]


def pytest_report_header() -> list[str]:
    from importlib.metadata import version

    res = []
    for pkg in VERSION_PKGS:
        pkg_version = version(pkg)
        path = __import__(pkg).__file__
        if path and "site-packages" in path:
            # Replace everything up to and including site-packages with site::
            parts = path.split("site-packages", 1)
            if len(parts) > 1:
                path = "site::" + parts[1]
        elif path and str(Path.cwd()) in path:
            # Replace current working directory with CWD::
            path = path.replace(str(Path.cwd()), "CWD::")
        res.append(f"{pkg} version {pkg_version} from {path}")
    return res


def pytest_addoption(parser: Any) -> None:
    group = parser.getgroup("setuptools_scm")
    group.addoption(
        "--test-legacy", dest="scm_test_virtualenv", default=False, action="store_true"
    )


class DebugMode(contextlib.AbstractContextManager):  # type: ignore[type-arg]
    from setuptools_scm import _log as __module

    def __init__(self) -> None:
        self.__stack = contextlib.ExitStack()

    def __enter__(self) -> Self:
        self.enable()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.disable()

    def enable(self) -> None:
        self.__stack.enter_context(self.__module.defer_to_pytest())

    def disable(self) -> None:
        self.__stack.close()


@pytest.fixture(autouse=True)
def debug_mode() -> Iterator[DebugMode]:
    with DebugMode() as debug_mode:
        yield debug_mode


def setup_git_wd(wd: WorkDir, monkeypatch: pytest.MonkeyPatch | None = None) -> WorkDir:
    """Set up a WorkDir with git initialized and configured for testing."""
    if monkeypatch:
        monkeypatch.delenv("HOME", raising=False)
    wd("git init")
    wd("git config user.email test@example.com")
    wd('git config user.name "a test"')
    wd.add_command = "git add ."
    wd.commit_command = "git commit -m test-{reason}"
    wd.tag_command = "git tag {tag}"
    return wd


def setup_hg_wd(wd: WorkDir) -> WorkDir:
    """Set up a WorkDir with mercurial initialized and configured for testing."""
    wd("hg init")
    wd.add_command = "hg add ."
    wd.commit_command = 'hg commit -m test-{reason} -u test -d "0 0"'
    wd.tag_command = "hg tag {tag}"
    return wd


@pytest.fixture
def wd(
    tmp_path: Path, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> WorkDir:
    """WorkDir fixture that automatically configures SCM based on markers."""
    target_wd = tmp_path.resolve() / "wd"
    target_wd.mkdir()
    wd = WorkDir(target_wd)

    # Check for SCM markers on the test function or module
    git_marker = request.node.get_closest_marker("git")
    hg_marker = request.node.get_closest_marker("hg")

    # Configure SCM based on markers
    if git_marker:
        setup_git_wd(wd, monkeypatch)
    elif hg_marker:
        setup_hg_wd(wd)
    # If no SCM markers, return unconfigured workdir

    return wd


@pytest.fixture(scope="session")
def hg_exe() -> str:
    hg = shutil.which("hg")
    if hg is None:
        pytest.skip("hg executable not found")
    return hg


@pytest.fixture
def repositories_hg_git(tmp_path: Path) -> tuple[WorkDir, WorkDir]:
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
    run(["hg", "clone", path_git, path_hg, "--config", "extensions.hggit="], tmp_path)
    assert path_hg.exists()

    with open(path_hg / ".hg/hgrc", "a") as file:
        file.write("[extensions]\nhggit =\n")

    wd_hg = WorkDir(path_hg)
    wd_hg.add_command = "hg add ."
    wd_hg.commit_command = 'hg commit -m test-{reason} -u test -d "0 0"'

    return wd_hg, wd
