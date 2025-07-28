from __future__ import annotations

import pprint
import subprocess
import sys

from dataclasses import replace
from importlib.metadata import EntryPoint
from importlib.metadata import distribution
from pathlib import Path
from typing import Sequence

import pytest

from setuptools_scm import Configuration
from setuptools_scm._run_cmd import run
from setuptools_scm.git import parse
from setuptools_scm.integration import data_from_mime
from setuptools_scm.version import meta


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
    run("git init", repo_path)

    # Create a nested directory with specific casing
    nested_dir = repo_path / "CasedDir"
    nested_dir.mkdir()

    # Create a pyproject.toml in the nested directory
    (nested_dir / "pyproject.toml").write_text("""
[build-system]
requires = ["setuptools>=64", "setuptools-scm"]
build-backend = "setuptools.build_meta"

[project]
name = "test-project"
dynamic = ["version"]

[tool.setuptools_scm]
""")

    # Add and commit the file
    run("git add .", repo_path)
    run("git commit -m 'Initial commit'", repo_path)

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


def test_case_mismatch_force_assertion_failure(tmp_path: Path) -> None:
    """Force the assertion failure by directly calling _git_toplevel with mismatched paths"""
    from setuptools_scm._file_finders.git import _git_toplevel

    # Create git repo structure
    repo_path = tmp_path / "my_repo"
    repo_path.mkdir()
    run("git init", repo_path)

    # Create nested directory
    nested_dir = repo_path / "CasedDir"
    nested_dir.mkdir()

    # Add and commit something to make it a valid repo
    (nested_dir / "test.txt").write_text("test")
    run("git add .", repo_path)
    run("git commit -m 'Initial commit'", repo_path)

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


def test_write_to_absolute_path_passes_when_subdir_of_root(tmp_path: Path) -> None:
    c = Configuration(root=tmp_path, write_to=tmp_path / "VERSION.py")
    v = meta("1.0", config=c)
    from setuptools_scm._get_version_impl import write_version_files

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
    from setuptools_scm._version_cls import _version_as_tuple

    assert _version_as_tuple(input) == expected
