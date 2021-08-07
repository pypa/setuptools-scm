import os
import sys

import py
import pytest

import setuptools_scm
from setuptools_scm import dump_version
from setuptools_scm.utils import data_from_mime
from setuptools_scm.utils import do


@pytest.mark.parametrize("cmd", ["ls", "dir"])
def test_do(cmd, tmpdir):
    if not py.path.local.sysfind(cmd):
        pytest.skip(cmd + " not found")
    do(cmd, str(tmpdir))


def test_data_from_mime(tmpdir):
    tmpfile = tmpdir.join("test.archival")
    tmpfile.write("name: test\nrevision: 1")

    res = data_from_mime(str(tmpfile))
    assert res == {"name": "test", "revision": "1"}


def test_version_from_pkginfo(wd, monkeypatch):
    wd.write("PKG-INFO", "Version: 0.1")

    assert wd.version == "0.1"

    # replicate issue 167
    assert wd.get_version(version_scheme="1.{0.distance}.0".format) == "0.1"


def assert_root(monkeypatch, expected_root):
    """
    Patch version_from_scm to simply assert that root is expected root
    """

    def assertion(config):
        assert config.absolute_root == expected_root

    monkeypatch.setattr(setuptools_scm, "_do_parse", assertion)


def test_root_parameter_creation(monkeypatch):
    assert_root(monkeypatch, os.getcwd())
    setuptools_scm.get_version()


def test_version_from_scm(wd):
    with pytest.warns(DeprecationWarning, match=".*version_from_scm.*"):
        setuptools_scm.version_from_scm(str(wd))


def test_root_parameter_pass_by(monkeypatch, tmpdir):
    assert_root(monkeypatch, tmpdir)
    setuptools_scm.get_version(root=tmpdir.strpath)


def test_parentdir_prefix(tmpdir, monkeypatch):
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")
    p = tmpdir.ensure("projectname-v12.34", dir=True)
    p.join("setup.py").write(
        """from setuptools import setup
setup(use_scm_version={"parentdir_prefix_version": "projectname-"})
"""
    )
    res = do((sys.executable, "setup.py", "--version"), p)
    assert res == "12.34"


def test_fallback(tmpdir, monkeypatch):
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")
    p = tmpdir.ensure("sub/package", dir=1)
    p.join("setup.py").write(
        """from setuptools import setup
setup(use_scm_version={"fallback_version": "12.34"})
"""
    )
    res = do((sys.executable, "setup.py", "--version"), p)
    assert res == "12.34"


@pytest.mark.parametrize(
    "version", ["1.0", "1.2.3.dev1+ge871260", "1.2.3.dev15+ge871260.d20180625", "2345"]
)
def test_pretended(version, monkeypatch):
    monkeypatch.setenv(setuptools_scm.PRETEND_KEY, version)
    assert setuptools_scm.get_version() == version


def test_root_relative_to(monkeypatch, tmp_path):
    assert_root(monkeypatch, str(tmp_path / "alt"))
    module = tmp_path / "module/file.py"
    module.parent.mkdir()
    module.touch()
    setuptools_scm.get_version(root="../alt", relative_to=str(module))
    with pytest.warns(UserWarning, match="relative_to is expected to be a file.*"):
        setuptools_scm.get_version(root="../alt", relative_to=str(module.parent))


def test_dump_version(tmpdir):
    sp = tmpdir.strpath

    dump_version(sp, "1.0", "first.txt")
    assert tmpdir.join("first.txt").read() == "1.0"

    dump_version(sp, "1.0.dev42", "first.py")
    content = tmpdir.join("first.py").read()
    lines = content.splitlines()
    assert "version = '1.0.dev42'" in lines
    assert "version_tuple = (1, 0, 'dev42')" in lines

    dump_version(sp, "1.0.1+g4ac9d2c", "second.py")
    content = tmpdir.join("second.py").read()
    lines = content.splitlines()
    assert "version = '1.0.1+g4ac9d2c'" in lines
    assert "version_tuple = (1, 0, 1, 'g4ac9d2c')" in lines

    dump_version(sp, "1.2.3.dev18+gb366d8b.d20210415", "third.py")
    content = tmpdir.join("third.py").read()
    lines = content.splitlines()
    assert "version = '1.2.3.dev18+gb366d8b.d20210415'" in lines
    assert "version_tuple = (1, 2, 3, 'dev18', 'gb366d8b.d20210415')" in lines

    import ast

    ast.parse(content)


def test_parse_plain_fails(recwarn):
    def parse(root):
        return "tricked you"

    with pytest.raises(TypeError):
        setuptools_scm.get_version(parse=parse)


def test_custom_version_cls():
    """Test that `normalize` and `version_cls` work as expected"""

    class MyVersion:
        def __init__(self, tag_str: str):
            self.version = tag_str

        def __repr__(self):
            return f"hello,{self.version}"

    # you can not use normalize=False and version_cls at the same time
    with pytest.raises(ValueError):
        setuptools_scm.get_version(normalize=False, version_cls=MyVersion)

    # TODO unfortunately with PRETEND_KEY the preformatted flag becomes True
    #  which bypasses our class. which other mechanism would be ok to use here
    #  to create a test?
    # monkeypatch.setenv(setuptools_scm.PRETEND_KEY, "1.0.1")
    # assert setuptools_scm.get_version(version_cls=MyVersion) == "1"
