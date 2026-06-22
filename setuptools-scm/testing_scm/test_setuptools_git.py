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


setup_py_unnormalized_sic: dict[str, str] = {
    "false": """
        from setuptools import setup
        setup(use_scm_version={'normalize': False, 'write_to': 'VERSION.txt'})
        """,
    "with_named_import": """
        from setuptools import setup
        setup(use_scm_version={
            'version_cls': 'setuptools_scm.NonNormalizedVersion',
            'write_to': 'VERSION.txt'
        })
        """,
}

setup_py_unnormalized_custom_cls: str = """
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
"""


@pytest.mark.parametrize(
    "setup_py_txt",
    [pytest.param(text, id=key) for key, text in setup_py_unnormalized_sic.items()],
)
def test_git_version_unnormalized_setuptools(
    setup_py_txt: str, wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Test that normalize=False / NonNormalizedVersion prevents setuptools
    from re-normalizing the version (via setuptools.sic wrapping).
    Both --version output and write_to files preserve the raw tag.
    """
    monkeypatch.setenv("SETUPTOOLS_SCM_WRITE_TO_SOURCE", "1")
    monkeypatch.chdir(wd.cwd)
    wd.write("setup.py", dedent(setup_py_txt))

    wd.commit_testfile()
    wd("git tag 17.33.0-rc1")

    res = wd([sys.executable, "setup.py", "--version"])
    assert res == "17.33.0-rc1"

    assert wd.cwd.joinpath("VERSION.txt").read_text(encoding="utf-8") == "17.33.0-rc1"


def test_git_version_unnormalized_custom_cls(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Test that a custom version_cls still gets write_to files un-normalized,
    but setuptools may normalize the dist metadata version (no sic wrapping
    for arbitrary custom classes).
    """
    monkeypatch.setenv("SETUPTOOLS_SCM_WRITE_TO_SOURCE", "1")
    monkeypatch.chdir(wd.cwd)
    wd.write("setup.py", dedent(setup_py_unnormalized_custom_cls))

    wd.commit_testfile()
    wd("git tag 17.33.0-rc1")

    res = wd([sys.executable, "setup.py", "--version"])
    assert res == "17.33.0rc1"

    assert wd.cwd.joinpath("VERSION.txt").read_text(encoding="utf-8") == "17.33.0-rc1"


@pytest.mark.issue(1354)
def test_calver_zero_padding_preserved_with_normalize_false(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Test that CalVer zero-padded versions (e.g. 2024.01.05) are preserved
    in dist.metadata.version when normalize=false.

    Without the sic() wrapping, setuptools' _normalize_version (which runs
    after our finalize_options hook) would strip '2024.01.05' to '2024.1.5'.

    Note: wheel filenames and dist-info METADATA are always canonicalized
    by the wheel builder (bdist_wheel.safer_version) — that is a PEP 427
    constraint outside setuptools-scm's control.
    """
    import subprocess
    import textwrap
    import zipfile

    monkeypatch.chdir(wd.cwd)

    wd.write(
        "pyproject.toml",
        textwrap.dedent("""\
            [build-system]
            requires = ["setuptools>=64", "setuptools-scm"]
            build-backend = "setuptools.build_meta"

            [project]
            name = "calver-test-pkg"
            dynamic = ["version"]

            [tool.setuptools_scm]
            version_scheme = "calver-by-date"
            normalize = false
            version_file = "calver_test_pkg/_version.py"

            [tool.setuptools.packages.find]
            where = ["."]
        """),
    )

    pkg_dir = wd.cwd / "calver_test_pkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")

    wd.commit_testfile()
    wd("git tag 2024.01.05")

    # --version uses dist.metadata.version which our sic() wrapping preserves
    res = wd(
        [
            sys.executable,
            "-c",
            dedent("""\
        from setuptools import Distribution
        import setuptools_scm._integration.setuptools  # ensure hooks registered
        d = Distribution(attrs={
            'name': 'calver-test-pkg',
        })
        d.parse_config_files()
        print(d.metadata.version)
    """),
        ]
    )
    assert res == "2024.01.05", (
        f"dist.metadata.version should preserve zero-padding, got: {res}"
    )

    # Build wheel — filename is canonicalized by PEP 427, but build succeeds
    build_result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--no-isolation"],
        cwd=wd.cwd,
        capture_output=True,
        text=True,
        check=False,
    )

    assert build_result.returncode == 0, (
        f"Build failed:\nstdout: {build_result.stdout}\nstderr: {build_result.stderr}"
    )

    dist_dir = wd.cwd / "dist"
    wheels = list(dist_dir.glob("*.whl"))
    assert len(wheels) == 1, f"Expected 1 wheel, found {len(wheels)}"

    # Version file inside the wheel should preserve zero-padded version
    with zipfile.ZipFile(wheels[0], "r") as whl:
        version_content = None
        for name in whl.namelist():
            if "_version.py" in name:
                version_content = whl.read(name).decode("utf-8")
                break

        assert version_content is not None, (
            f"Version file not found in wheel. Contents: {whl.namelist()}"
        )
        assert "2024.01.05" in version_content, (
            f"Version file should contain zero-padded version.\n"
            f"Content:\n{version_content}"
        )


@pytest.mark.issue(193)
@pytest.mark.issue(620)
@pytest.mark.xfail(
    sys.platform == "win32",
    reason="subprocess fails with NotADirectoryError in git worktrees on Windows",
)
def test_git_worktree_support(wd: WorkDir, tmp_path: Path) -> None:

    wd.commit_testfile()
    worktree = tmp_path / "work_tree"
    wd(f"git worktree add -b work-tree {worktree}")

    res = run([sys.executable, "-m", "setuptools_scm", "ls"], cwd=worktree)
    assert "test.txt" in res.stdout
