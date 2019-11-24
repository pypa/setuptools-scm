import sys

from setuptools_scm.utils import do


def test_pyproject_support(tmpdir, monkeypatch):
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")
    pkg = tmpdir.ensure("package", dir=42)
    pkg.join("pyproject.toml").write(
        """[tool.setuptools_scm]
enabled = true
fallback_version = "12.34"
"""
    )
    pkg.join("setup.py").write("__import__('setuptools').setup()")
    res = do((sys.executable, "setup.py", "--version"), pkg)
    assert res == "12.34"
