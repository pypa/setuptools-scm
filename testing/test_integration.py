import sys
import os

import pytest

from setuptools_scm.utils import do
from setuptools_scm import PRETEND_KEY, PRETEND_KEY_NAMED


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
    pkg.join("pyproject.toml").write(
        """[tool.setuptools_scm]
fallback_version = "12.34"
"""
    )
    pkg.join("setup.py").write("__import__('setuptools').setup()")
    res = do((sys.executable, "setup.py", "--version"), pkg)
    assert res == "12.34"


def test_pyproject_support_with_git(tmpdir, monkeypatch, wd):
    pytest.importorskip("toml")
    pkg = tmpdir.join("wd")
    pkg.join("pyproject.toml").write("""[tool.setuptools_scm]""")
    pkg.join("setup.py").write(
        "__import__('setuptools').setup(name='setuptools_scm_example')"
    )
    res = do((sys.executable, "setup.py", "--version"), pkg)
    assert res.endswith("0.1.dev0")


def test_pretend_version(tmpdir, monkeypatch, wd):
    monkeypatch.setenv(PRETEND_KEY, "1.0.0")

    assert wd.get_version() == "1.0.0"
    assert wd.get_version(dist_name="ignored") == "1.0.0"


def test_pretend_version_named_pyproject_integration(tmpdir, monkeypatch, wd):
    test_pyproject_support_with_git(tmpdir, monkeypatch, wd)
    monkeypatch.setenv(
        PRETEND_KEY_NAMED.format(name="setuptools_scm_example".upper()), "3.2.1"
    )
    res = do((sys.executable, "setup.py", "--version"), tmpdir / "wd")
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


def test_own_setup_fails_on_old_python(monkeypatch):
    monkeypatch.setattr("sys.version_info", (3, 5))
    monkeypatch.syspath_prepend(os.path.dirname(os.path.dirname(__file__)))

    import setup

    with pytest.raises(
        RuntimeError,
        match="support for python < 3.6 has been removed in setuptools_scm>=6.0.0",
    ):
        setup.scm_config()
