"""
Pytest plugin and test API for vcs_versioning.

This module can be used as a pytest plugin by adding to conftest.py:
    pytest_plugins = ["vcs_versioning.test_api"]
"""

from __future__ import annotations

import contextlib
import os
import shutil
import sys
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType

import pytest

from ._run_cmd import run

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

# Re-export WorkDir from _test_utils module
from ._test_utils import WorkDir

__all__ = [
    "TEST_SOURCE_DATE",
    "TEST_SOURCE_DATE_EPOCH",
    "TEST_SOURCE_DATE_FORMATTED",
    "TEST_SOURCE_DATE_TIMESTAMP",
    "DebugMode",
    "WorkDir",
    "debug_mode",
    "hg_exe",
    "repositories_hg_git",
    "wd",
]

# Test time constants: 2009-02-13T23:31:30+00:00
TEST_SOURCE_DATE = datetime(2009, 2, 13, 23, 31, 30, tzinfo=timezone.utc)
TEST_SOURCE_DATE_EPOCH = int(TEST_SOURCE_DATE.timestamp())
TEST_SOURCE_DATE_FORMATTED = "20090213"  # As used in node-and-date local scheme
TEST_SOURCE_DATE_TIMESTAMP = (
    "20090213233130"  # As used in node-and-timestamp local scheme
)


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest for vcs_versioning tests."""
    # 2009-02-13T23:31:30+00:00
    os.environ["SOURCE_DATE_EPOCH"] = str(TEST_SOURCE_DATE_EPOCH)
    os.environ["VCS_VERSIONING_DEBUG"] = "1"
    # Clear pretend version env vars so tests run real version detection
    # (Debian sets SETUPTOOLS_SCM_PRETEND_VERSION during package builds)
    for key in ("SETUPTOOLS_SCM_PRETEND_VERSION", "VCS_VERSIONING_PRETEND_VERSION"):
        os.environ.pop(key, None)


@pytest.fixture(scope="session", autouse=True)
def _global_overrides_context() -> Iterator[None]:
    """Automatically apply GlobalOverrides context for all tests.

    This ensures that SOURCE_DATE_EPOCH and debug settings from pytest_configure
    are properly picked up by the override system.
    """
    from .overrides import GlobalOverrides

    # Use SETUPTOOLS_SCM prefix for backwards compatibility.
    # EnvReader will also check VCS_VERSIONING as a fallback.
    with GlobalOverrides.from_env("SETUPTOOLS_SCM"):
        yield


class DebugMode(contextlib.AbstractContextManager):  # type: ignore[type-arg]
    """Context manager to enable debug logging for tests."""

    from . import _log as __module

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
    """Fixture to enable debug mode for all tests."""
    with DebugMode() as debug_mode:
        yield debug_mode


@pytest.fixture
def wd(tmp_path: Path) -> WorkDir:
    """Base WorkDir fixture that returns an unconfigured working directory.

    Individual test modules should override this fixture to set up specific SCM configurations.
    """
    target_wd = tmp_path.resolve() / "wd"
    target_wd.mkdir()
    return WorkDir(target_wd)


@pytest.fixture(scope="session")
def hg_exe() -> str:
    """Fixture to get the hg executable path, skipping if not found."""
    hg = shutil.which("hg")
    if hg is None:
        pytest.skip("hg executable not found")
    return hg


@pytest.fixture
def repositories_hg_git(tmp_path: Path) -> tuple[WorkDir, WorkDir]:
    """Fixture to create paired git and hg repositories for hg-git tests."""
    tmp_path = tmp_path.resolve()
    path_git = tmp_path / "repo_git"
    path_git.mkdir()

    wd = WorkDir(path_git).setup_git()

    path_hg = tmp_path / "repo_hg"
    run(["hg", "clone", path_git, path_hg, "--config", "extensions.hggit="], tmp_path)
    assert path_hg.exists()

    with open(path_hg / ".hg/hgrc", "a") as file:
        file.write("[extensions]\nhggit =\n")

    wd_hg = WorkDir(path_hg)
    wd_hg.configure_hg_commands()

    return wd_hg, wd
