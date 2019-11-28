import sys

import pytest

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
    pkg.join("pyproject.toml").write(
        """[tool.setuptools_scm]
fallback_version = "12.34"
"""
    )
    pkg.join("setup.py").write("__import__('setuptools').setup()")
    res = do((sys.executable, "setup.py", "--version"), pkg)
    assert res == "12.34"


def test_pyproject_support_with_git(tmpdir, monkeypatch, wd):
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")
    pkg = tmpdir.join("wd")
    pkg.join("pyproject.toml").write("""[tool.setuptools_scm]""")
    pkg.join("setup.py").write("__import__('setuptools').setup()")
    res = do((sys.executable, "setup.py", "--version"), pkg)
    assert res == "0.1.dev0"
