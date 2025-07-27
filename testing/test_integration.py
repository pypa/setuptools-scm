from __future__ import annotations

import importlib.metadata
import os
import subprocess
import sys
import textwrap

from pathlib import Path

import pytest

import setuptools_scm._integration.setuptools

from setuptools_scm import Configuration
from setuptools_scm._integration.setuptools import _extract_package_name
from setuptools_scm._integration.setuptools import _warn_on_old_setuptools
from setuptools_scm._overrides import PRETEND_KEY
from setuptools_scm._overrides import PRETEND_KEY_NAMED
from setuptools_scm._run_cmd import run

from .wd_wrapper import WorkDir

c = Configuration()


@pytest.fixture
def wd(wd: WorkDir) -> WorkDir:
    wd("git init")
    wd("git config user.email test@example.com")
    wd('git config user.name "a test"')
    wd.add_command = "git add ."
    wd.commit_command = "git commit -m test-{reason}"
    return wd


def test_pyproject_support(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if sys.version_info < (3, 11):
        pytest.importorskip("tomli")
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")
    pkg = tmp_path / "package"
    pkg.mkdir()
    pkg.joinpath("pyproject.toml").write_text(
        textwrap.dedent(
            """
            [tool.setuptools_scm]
            fallback_version = "12.34"
            [project]
            name = "foo"
            description = "Factory ⸻ A code generator 🏭"
            authors = [{name = "Łukasz Langa"}]
            dynamic = ["version"]
            """
        ),
        encoding="utf-8",
    )
    pkg.joinpath("setup.py").write_text(
        "__import__('setuptools').setup()", encoding="utf-8"
    )
    res = run([sys.executable, "setup.py", "--version"], pkg)
    assert res.stdout == "12.34"


PYPROJECT_FILES = {
    "setup.py": "[tool.setuptools_scm]",
    "setup.cfg": "[tool.setuptools_scm]",
    "pyproject tool.setuptools_scm": (
        "[tool.setuptools_scm]\ndist_name='setuptools_scm_example'"
    ),
    "pyproject.project": (
        "[project]\nname='setuptools_scm_example'\n"
        "dynamic=['version']\n[tool.setuptools_scm]"
    ),
}

SETUP_PY_PLAIN = "__import__('setuptools').setup()"
SETUP_PY_WITH_NAME = "__import__('setuptools').setup(name='setuptools_scm_example')"

SETUP_PY_FILES = {
    "setup.py": SETUP_PY_WITH_NAME,
    "setup.cfg": SETUP_PY_PLAIN,
    "pyproject tool.setuptools_scm": SETUP_PY_PLAIN,
    "pyproject.project": SETUP_PY_PLAIN,
}

SETUP_CFG_FILES = {
    "setup.py": "",
    "setup.cfg": "[metadata]\nname=setuptools_scm_example",
    "pyproject tool.setuptools_scm": "",
    "pyproject.project": "",
}

with_metadata_in = pytest.mark.parametrize(
    "metadata_in",
    ["setup.py", "setup.cfg", "pyproject tool.setuptools_scm", "pyproject.project"],
)


@with_metadata_in
def test_pyproject_support_with_git(wd: WorkDir, metadata_in: str) -> None:
    if sys.version_info < (3, 11):
        pytest.importorskip("tomli")
    wd.write("pyproject.toml", PYPROJECT_FILES[metadata_in])
    wd.write("setup.py", SETUP_PY_FILES[metadata_in])
    wd.write("setup.cfg", SETUP_CFG_FILES[metadata_in])
    res = wd([sys.executable, "setup.py", "--version"])
    assert res.endswith("0.1.dev0+d20090213")


@pytest.mark.parametrize("use_scm_version", ["True", "{}", "lambda: {}"])
def test_pyproject_missing_setup_hook_works(wd: WorkDir, use_scm_version: str) -> None:
    wd.write(
        "setup.py",
        f"""__import__('setuptools').setup(
    name="example-scm-unique",
    use_scm_version={use_scm_version},
    )""",
    )
    wd.write(
        "pyproject.toml",
        textwrap.dedent(
            """
            [build-system]
            requires=["setuptools", "setuptools_scm"]
            build-backend = "setuptools.build_meta"
            [tool]
            """
        ),
    )

    res = subprocess.run(
        [sys.executable, "setup.py", "--version"],
        cwd=wd.cwd,
        check=True,
        stdout=subprocess.PIPE,
        encoding="utf-8",
    )
    stripped = res.stdout.strip()
    assert stripped.endswith("0.1.dev0+d20090213")

    res_build = subprocess.run(
        [sys.executable, "-m", "build", "-nxw"],
        env={k: v for k, v in os.environ.items() if k != "SETUPTOOLS_SCM_DEBUG"},
        cwd=wd.cwd,
    )
    import pprint

    pprint.pprint(res_build)
    wheel: Path = next(wd.cwd.joinpath("dist").iterdir())
    assert "0.1.dev0+d20090213" in str(wheel)


def test_pretend_version(monkeypatch: pytest.MonkeyPatch, wd: WorkDir) -> None:
    monkeypatch.setenv(PRETEND_KEY, "1.0.0")

    assert wd.get_version() == "1.0.0"
    assert wd.get_version(dist_name="ignored") == "1.0.0"


@with_metadata_in
def test_pretend_version_named_pyproject_integration(
    monkeypatch: pytest.MonkeyPatch, wd: WorkDir, metadata_in: str
) -> None:
    test_pyproject_support_with_git(wd, metadata_in)
    monkeypatch.setenv(
        PRETEND_KEY_NAMED.format(name="setuptools_scm_example".upper()), "3.2.1"
    )
    res = wd([sys.executable, "setup.py", "--version"])
    assert res.endswith("3.2.1")


def test_pretend_version_named(monkeypatch: pytest.MonkeyPatch, wd: WorkDir) -> None:
    monkeypatch.setenv(PRETEND_KEY_NAMED.format(name="test".upper()), "1.0.0")
    monkeypatch.setenv(PRETEND_KEY_NAMED.format(name="test2".upper()), "2.0.0")
    assert wd.get_version(dist_name="test") == "1.0.0"
    assert wd.get_version(dist_name="test2") == "2.0.0"


def test_pretend_version_name_takes_precedence(
    monkeypatch: pytest.MonkeyPatch, wd: WorkDir
) -> None:
    monkeypatch.setenv(PRETEND_KEY_NAMED.format(name="test".upper()), "1.0.0")
    monkeypatch.setenv(PRETEND_KEY, "2.0.0")
    assert wd.get_version(dist_name="test") == "1.0.0"


def test_pretend_version_accepts_bad_string(
    monkeypatch: pytest.MonkeyPatch, wd: WorkDir
) -> None:
    monkeypatch.setenv(PRETEND_KEY, "dummy")
    wd.write("setup.py", SETUP_PY_PLAIN)
    assert wd.get_version(write_to="test.py") == "dummy"
    pyver = wd([sys.executable, "setup.py", "--version"])
    assert pyver == "0.0.0"


def testwarn_on_broken_setuptools() -> None:
    _warn_on_old_setuptools("61")
    with pytest.warns(RuntimeWarning, match="ERROR: setuptools==60"):
        _warn_on_old_setuptools("60")


@pytest.mark.issue(611)
def test_distribution_provides_extras() -> None:
    from importlib.metadata import distribution

    dist = distribution("setuptools_scm")
    pe: list[str] = dist.metadata.get_all("Provides-Extra", [])
    assert sorted(pe) == ["docs", "rich", "test", "toml"]


@pytest.mark.issue(760)
def test_unicode_in_setup_cfg(tmp_path: Path) -> None:
    cfg = tmp_path / "setup.cfg"
    cfg.write_text(
        textwrap.dedent(
            """
            [metadata]
            name = configparser
            author = Łukasz Langa
            """
        ),
        encoding="utf-8",
    )
    name = setuptools_scm._integration.setuptools.read_dist_name_from_setup_cfg(cfg)
    assert name == "configparser"


def test_setuptools_version_keyword_ensures_regex(
    wd: WorkDir,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd.commit_testfile("test")
    wd("git tag 1.0")
    monkeypatch.chdir(wd.cwd)
    import setuptools

    from setuptools_scm._integration.setuptools import version_keyword

    dist = setuptools.Distribution({"name": "test"})
    version_keyword(dist, "use_scm_version", {"tag_regex": "(1.0)"})


@pytest.mark.parametrize(
    "ep_name", ["setuptools_scm.parse_scm", "setuptools_scm.parse_scm_fallback"]
)
def test_git_archival_plugin_ignored(tmp_path: Path, ep_name: str) -> None:
    tmp_path.joinpath(".git_archival.txt").write_text("broken", encoding="utf-8")
    try:
        dist = importlib.metadata.distribution("setuptools_scm_git_archive")
    except importlib.metadata.PackageNotFoundError:
        pytest.skip("setuptools_scm_git_archive not installed")
    else:
        print(dist.metadata["Name"], dist.version)
    from setuptools_scm.discover import iter_matching_entrypoints

    found = list(iter_matching_entrypoints(tmp_path, config=c, entrypoint=ep_name))
    imports = [item.value for item in found]
    assert "setuptools_scm_git_archive:parse" not in imports


def test_pyproject_build_system_requires_setuptools_scm(wd: WorkDir) -> None:
    """Test that setuptools_scm is enabled when present in build-system.requires"""
    if sys.version_info < (3, 11):
        pytest.importorskip("tomli")

    # Test with setuptools_scm in build-system.requires but no [tool.setuptools_scm] section
    wd.write(
        "pyproject.toml",
        textwrap.dedent(
            """
            [build-system]
            requires = ["setuptools>=64", "setuptools_scm>=8"]
            build-backend = "setuptools.build_meta"

            [project]
            name = "test-package"
            dynamic = ["version"]
            """
        ),
    )
    wd.write("setup.py", "__import__('setuptools').setup()")

    res = wd([sys.executable, "setup.py", "--version"])
    assert res.endswith("0.1.dev0+d20090213")


def test_pyproject_build_system_requires_setuptools_scm_dash_variant(
    wd: WorkDir,
) -> None:
    """Test that setuptools-scm (dash variant) is also detected in build-system.requires"""
    if sys.version_info < (3, 11):
        pytest.importorskip("tomli")

    # Test with setuptools-scm (dash variant) in build-system.requires
    wd.write(
        "pyproject.toml",
        textwrap.dedent(
            """
            [build-system]
            requires = ["setuptools>=64", "setuptools-scm>=8"]
            build-backend = "setuptools.build_meta"

            [project]
            name = "test-package"
            dynamic = ["version"]
            """
        ),
    )
    wd.write("setup.py", "__import__('setuptools').setup()")

    res = wd([sys.executable, "setup.py", "--version"])
    assert res.endswith("0.1.dev0+d20090213")


def test_pyproject_build_system_requires_with_extras(wd: WorkDir) -> None:
    """Test that setuptools_scm[toml] is detected in build-system.requires"""
    if sys.version_info < (3, 11):
        pytest.importorskip("tomli")

    # Test with setuptools_scm[toml] (with extras) in build-system.requires
    wd.write(
        "pyproject.toml",
        textwrap.dedent(
            """
            [build-system]
            requires = ["setuptools>=64", "setuptools_scm[toml]>=8"]
            build-backend = "setuptools.build_meta"

            [project]
            name = "test-package"
            dynamic = ["version"]
            """
        ),
    )
    wd.write("setup.py", "__import__('setuptools').setup()")

    res = wd([sys.executable, "setup.py", "--version"])
    assert res.endswith("0.1.dev0+d20090213")


def test_pyproject_build_system_requires_not_present(wd: WorkDir) -> None:
    """Test that version is not set when setuptools_scm is not in build-system.requires and no [tool.setuptools_scm] section"""
    if sys.version_info < (3, 11):
        pytest.importorskip("tomli")

    # Test without setuptools_scm in build-system.requires and no [tool.setuptools_scm] section
    wd.write(
        "pyproject.toml",
        textwrap.dedent(
            """
            [build-system]
            requires = ["setuptools>=64", "wheel"]
            build-backend = "setuptools.build_meta"

            [project]
            name = "test-package"
            dynamic = ["version"]
            """
        ),
    )
    wd.write("setup.py", "__import__('setuptools').setup()")

    res = wd([sys.executable, "setup.py", "--version"])
    assert res == "0.0.0"


def test_pyproject_build_system_requires_priority_over_tool_section(
    wd: WorkDir,
) -> None:
    """Test that both build-system.requires and [tool.setuptools_scm] section work together"""
    if sys.version_info < (3, 11):
        pytest.importorskip("tomli")

    # Test with both setuptools_scm in build-system.requires AND [tool.setuptools_scm] section
    wd.write(
        "pyproject.toml",
        textwrap.dedent(
            """
            [build-system]
            requires = ["setuptools>=64", "setuptools_scm>=8"]
            build-backend = "setuptools.build_meta"

            [project]
            name = "test-package"
            dynamic = ["version"]

            [tool.setuptools_scm]
            # empty section, should work with build-system detection
            """
        ),
    )
    wd.write("setup.py", "__import__('setuptools').setup()")

    res = wd([sys.executable, "setup.py", "--version"])
    assert res.endswith("0.1.dev0+d20090213")


def test_extract_package_name() -> None:
    """Test the _extract_package_name helper function"""
    assert _extract_package_name("setuptools_scm") == "setuptools_scm"
    assert _extract_package_name("setuptools-scm") == "setuptools-scm"
    assert _extract_package_name("setuptools_scm>=8") == "setuptools_scm"
    assert _extract_package_name("setuptools-scm>=8") == "setuptools-scm"
    assert _extract_package_name("setuptools_scm[toml]>=7.0") == "setuptools_scm"
    assert _extract_package_name("setuptools-scm[toml]>=7.0") == "setuptools-scm"
    assert _extract_package_name("setuptools_scm==8.0.0") == "setuptools_scm"
    assert _extract_package_name("setuptools_scm~=8.0") == "setuptools_scm"
    assert _extract_package_name("setuptools_scm[rich,toml]>=8") == "setuptools_scm"


def test_build_requires_integration_with_config_reading(wd: WorkDir) -> None:
    """Test that Configuration.from_file handles build-system.requires automatically"""
    if sys.version_info < (3, 11):
        pytest.importorskip("tomli")

    from setuptools_scm._config import Configuration

    # Test: pyproject.toml with setuptools_scm in build-system.requires but no tool section
    wd.write(
        "pyproject.toml",
        textwrap.dedent(
            """
            [build-system]
            requires = ["setuptools>=64", "setuptools_scm>=8"]

            [project]
            name = "test-package"
            """
        ),
    )

    # This should NOT raise an error because setuptools_scm is in build-system.requires
    config = Configuration.from_file(
        name=wd.cwd.joinpath("pyproject.toml"), dist_name="test-package"
    )
    assert config.dist_name == "test-package"

    # Test: pyproject.toml with setuptools-scm (dash variant) in build-system.requires
    wd.write(
        "pyproject.toml",
        textwrap.dedent(
            """
            [build-system]
            requires = ["setuptools>=64", "setuptools-scm>=8"]

            [project]
            name = "test-package"
            """
        ),
    )

    # This should also NOT raise an error
    config = Configuration.from_file(
        name=wd.cwd.joinpath("pyproject.toml"), dist_name="test-package"
    )
    assert config.dist_name == "test-package"


def test_improved_error_message_mentions_both_config_options(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that the error message mentions both configuration options"""
    if sys.version_info < (3, 11):
        pytest.importorskip("tomli")

    # Create pyproject.toml without setuptools_scm configuration
    wd.write(
        "pyproject.toml",
        textwrap.dedent(
            """
            [project]
            name = "test-package"

            [build-system]
            requires = ["setuptools>=64"]
            """
        ),
    )

    from setuptools_scm._config import Configuration

    with pytest.raises(LookupError) as exc_info:
        Configuration.from_file(
            name=wd.cwd.joinpath("pyproject.toml"),
            dist_name="test-package",
            missing_file_ok=False,
        )

    error_msg = str(exc_info.value)
    # Check that the error message mentions both configuration options
    assert "tool.setuptools_scm" in error_msg
    assert "build-system" in error_msg
    assert "requires" in error_msg
