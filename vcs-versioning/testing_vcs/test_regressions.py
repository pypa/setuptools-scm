"""Core VCS regression tests."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import pytest
from setuptools_scm import Configuration
from setuptools_scm.git import parse
from setuptools_scm.version import meta
from vcs_versioning._run_cmd import run
from vcs_versioning.test_api import WorkDir


@pytest.mark.skipif(sys.platform != "win32", reason="this bug is only valid on windows")
def test_case_mismatch_on_windows_git(tmp_path: Path) -> None:
    """Case insensitive path checks on Windows"""
    camel_case_path = tmp_path / "CapitalizedDir"
    camel_case_path.mkdir()
    run("git init", camel_case_path)
    res = parse(str(camel_case_path).lower(), Configuration())
    assert res is not None


@pytest.mark.skipif(sys.platform != "win32", reason="this bug is only valid on windows")
def test_case_mismatch_nested_dir_windows_git(tmp_path: Path) -> None:
    """Test case where we have a nested directory with different casing"""
    # Create git repo in my_repo
    repo_path = tmp_path / "my_repo"
    repo_path.mkdir()
    wd = WorkDir(repo_path).setup_git()

    # Create a nested directory with specific casing
    nested_dir = repo_path / "CasedDir"
    nested_dir.mkdir()

    # Create a pyproject.toml in the nested directory
    wd.write(
        "CasedDir/pyproject.toml",
        """
[build-system]
requires = ["setuptools>=64", "setuptools-scm"]
build-backend = "setuptools.build_meta"

[project]
name = "test-project"
dynamic = ["version"]

[tool.setuptools_scm]
""",
    )

    # Add and commit the file
    wd.add_and_commit("Initial commit")

    # Now try to parse from the nested directory with lowercase path
    # This simulates: cd my_repo/caseddir (lowercase) when actual dir is CasedDir
    lowercase_nested_path = str(nested_dir).replace("CasedDir", "caseddir")

    # This should trigger the assertion error in _git_toplevel
    try:
        res = parse(lowercase_nested_path, Configuration())
        # If we get here without assertion error, the bug is already fixed or not triggered
        print(f"Parse succeeded with result: {res}")
    except AssertionError as e:
        print(f"AssertionError caught as expected: {e}")
        # Re-raise so the test fails, showing we reproduced the bug
        raise


def test_write_to_absolute_path_passes_when_subdir_of_root(tmp_path: Path) -> None:
    c = Configuration(root=tmp_path, write_to=tmp_path / "VERSION.py")
    v = meta("1.0", config=c)
    from vcs_versioning._get_version_impl import write_version_files

    with pytest.warns(DeprecationWarning, match=".*write_to=.* is a absolute.*"):
        write_version_files(c, "1.0", v)
    write_version_files(replace(c, write_to="VERSION.py"), "1.0", v)
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    with pytest.raises(
        # todo: python version specific error list
        ValueError,
        match=r".*VERSION.py' .* .*subdir.*",
    ):
        write_version_files(replace(c, root=subdir), "1.0", v)


@pytest.mark.parametrize(
    ("input", "expected"),
    [
        ("1.0", (1, 0)),
        ("1.0a2", (1, 0, "a2")),
        ("1.0.b2dev1", (1, 0, "b2", "dev1")),
        ("1.0.dev1", (1, 0, "dev1")),
    ],
)
def test_version_as_tuple(input: str, expected: Sequence[int | str]) -> None:
    from vcs_versioning._version_cls import _version_as_tuple

    assert _version_as_tuple(input) == expected
