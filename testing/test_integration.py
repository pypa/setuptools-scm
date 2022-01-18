import os
import sys
import textwrap

import pytest

from setuptools_scm import PRETEND_KEY
from setuptools_scm import PRETEND_KEY_NAMED
from setuptools_scm.integration import _warn_on_old_setuptools
from setuptools_scm.utils import do


@pytest.fixture
def wd(wd):
    wd("git init")
    wd("git config user.email test@example.com")
    wd('git config user.name "a test"')
    wd.add_command = "git add ."
    wd.commit_command = "git commit -m test-{reason}"
    return wd


def test_pyproject_support(tmpdir, monkeypatch):
    pytest.importorskip("toml")
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")
    pkg = tmpdir.ensure("package", dir=42)
    pkg.join("pyproject.toml").write_text(
        textwrap.dedent(
            """
            [tool.setuptools_scm]
            fallback_version = "12.34"
            [project]
            description = "Factory ⸻ A code generator 🏭"
            authors = [{name = "Łukasz Langa"}]
            """
        ),
        encoding="utf-8",
    )
    pkg.join("setup.py").write("__import__('setuptools').setup()")
    res = do((sys.executable, "setup.py", "--version"), pkg)
    assert res == "12.34"


PYPROJECT_FILES = {
    "setup.py": "[tool.setuptools_scm]",
    "setup.cfg": "[tool.setuptools_scm]",
    "pyproject tool.setuptools_scm": (
        "[tool.setuptools_scm]\ndist_name='setuptools_scm_example'"
    ),
    "pyproject.project": (
        "[project]\nname='setuptools_scm_example'\n[tool.setuptools_scm]"
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
def test_pyproject_support_with_git(wd, metadata_in):
    pytest.importorskip("tomli")
    wd.write("pyproject.toml", PYPROJECT_FILES[metadata_in])
    wd.write("setup.py", SETUP_PY_FILES[metadata_in])
    wd.write("setup.cfg", SETUP_CFG_FILES[metadata_in])
    res = wd((sys.executable, "setup.py", "--version"))
    assert res.endswith("0.1.dev0")


def test_pretend_version(monkeypatch, wd):
    monkeypatch.setenv(PRETEND_KEY, "1.0.0")

    assert wd.get_version() == "1.0.0"
    assert wd.get_version(dist_name="ignored") == "1.0.0"


@with_metadata_in
def test_pretend_version_named_pyproject_integration(monkeypatch, wd, metadata_in):
    test_pyproject_support_with_git(wd, metadata_in)
    monkeypatch.setenv(
        PRETEND_KEY_NAMED.format(name="setuptools_scm_example".upper()), "3.2.1"
    )
    res = wd((sys.executable, "setup.py", "--version"))
    assert res.endswith("3.2.1")


def test_pretend_version_named(tmpdir, monkeypatch, wd):
    monkeypatch.setenv(PRETEND_KEY_NAMED.format(name="test".upper()), "1.0.0")
    monkeypatch.setenv(PRETEND_KEY_NAMED.format(name="test2".upper()), "2.0.0")
    assert wd.get_version(dist_name="test") == "1.0.0"
    assert wd.get_version(dist_name="test2") == "2.0.0"


def test_pretend_version_name_takes_precedence(tmpdir, monkeypatch, wd):
    monkeypatch.setenv(PRETEND_KEY_NAMED.format(name="test".upper()), "1.0.0")
    monkeypatch.setenv(PRETEND_KEY, "2.0.0")
    assert wd.get_version(dist_name="test") == "1.0.0"


def test_pretend_version_accepts_bad_string(monkeypatch, wd):
    monkeypatch.setenv(PRETEND_KEY, "dummy")
    wd.write("setup.py", SETUP_PY_PLAIN)
    assert wd.get_version(write_to="test.py") == "dummy"
    assert wd("python setup.py --version") == "0.0.0"


def test_own_setup_fails_on_old_python(monkeypatch):
    monkeypatch.setattr("sys.version_info", (3, 5))
    monkeypatch.syspath_prepend(os.path.dirname(os.path.dirname(__file__)))

    import setup

    with pytest.raises(
        RuntimeError,
        match="support for python < 3.6 has been removed in setuptools_scm>=6.0.0",
    ):
        setup.scm_version()


def testwarn_on_broken_setuptools():
    _warn_on_old_setuptools("45")
    with pytest.warns(RuntimeWarning, match="ERROR: setuptools==44"):
        _warn_on_old_setuptools("44")


@pytest.mark.issue(611)
def test_distribution_procides_extras():
    try:
        from importlib.metadata import distribution
    except ImportError:
        from importlib_metadata import distribution

    dist = distribution("setuptools_scm")
    assert sorted(dist.metadata.get_all("Provides-Extra")) == ["test", "toml"]
