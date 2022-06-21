from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

import setuptools_scm
from setuptools_scm import dump_version
from setuptools_scm.config import Configuration
from setuptools_scm.utils import data_from_mime
from setuptools_scm.utils import do
from setuptools_scm.version import ScmVersion
from testing.wd_wrapper import WorkDir


@pytest.mark.parametrize("cmd", ["ls", "dir"])
def test_do(cmd: str, tmp_path: Path) -> None:
    if not shutil.which(cmd):
        pytest.skip(f"{cmd} not found")
    do(cmd, cwd=tmp_path)


def test_data_from_mime(tmp_path: Path) -> None:
    tmpfile = tmp_path.joinpath("test.archival")
    tmpfile.write_text("name: test\nrevision: 1")

    res = data_from_mime(str(tmpfile))
    assert res == {"name": "test", "revision": "1"}


def test_version_from_pkginfo(wd: WorkDir) -> None:
    wd.write("PKG-INFO", "Version: 0.1")

    assert wd.version == "0.1"

    # replicate issue 167
    assert wd.get_version(version_scheme="1.{0.distance}.0".format) == "0.1"


def assert_root(monkeypatch: pytest.MonkeyPatch, expected_root: str) -> None:
    """
    Patch version_from_scm to simply assert that root is expected root
    """

    def assertion(config: Configuration) -> ScmVersion:
        assert config.absolute_root == expected_root
        return ScmVersion("1.0", config=config)

    monkeypatch.setattr(setuptools_scm, "_do_parse", assertion)


def test_root_parameter_creation(monkeypatch: pytest.MonkeyPatch) -> None:
    assert_root(monkeypatch, os.getcwd())
    setuptools_scm.get_version()


def test_version_from_scm(wd: WorkDir) -> None:
    with pytest.warns(DeprecationWarning, match=".*version_from_scm.*"):
        setuptools_scm.version_from_scm(str(wd))


def test_root_parameter_pass_by(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    assert_root(monkeypatch, os.fspath(tmp_path))
    setuptools_scm.get_version(root=os.fspath(tmp_path))
    setuptools_scm.get_version(
        os.fspath(tmp_path)
    )  # issue 669 - posarg difference between Configuration and get_version


def test_parentdir_prefix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")
    p = tmp_path.joinpath("projectname-v12.34")
    p.mkdir()
    p.joinpath("setup.py").write_text(
        """from setuptools import setup
setup(use_scm_version={"parentdir_prefix_version": "projectname-"})
"""
    )
    res = do([sys.executable, "setup.py", "--version"], p)
    assert res == "12.34"


def test_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")
    p = tmp_path / "sub/package"
    p.mkdir(parents=True)
    p.joinpath("setup.py").write_text(
        """from setuptools import setup
setup(use_scm_version={"fallback_version": "12.34"})
"""
    )
    res = do([sys.executable, "setup.py", "--version"], p)
    assert res == "12.34"


def test_empty_pretend_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")
    monkeypatch.setenv("SETUPTOOLS_SCM_PRETEND_VERSION", "")
    p = tmp_path / "sub/package"
    p.mkdir(parents=True)
    p.joinpath("setup.py").write_text(
        """from setuptools import setup
setup(use_scm_version={"fallback_version": "12.34"})
"""
    )
    res = do([sys.executable, "setup.py", "--version"], p)
    assert res == "12.34"


def test_empty_pretend_version_named(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")
    monkeypatch.setenv("SETUPTOOLS_SCM_PRETEND_VERSION", "1.23")
    monkeypatch.setenv("SETUPTOOLS_SCM_PRETEND_VERSION_FOR_MYSCM", "")
    p = tmp_path.joinpath("sub/package")
    p.mkdir(parents=True)

    p.joinpath("setup.py").write_text(
        """from setuptools import setup
setup(name="myscm", use_scm_version={"fallback_version": "12.34"})
"""
    )
    res = do([sys.executable, "setup.py", "--version"], p)
    assert res == "12.34"


@pytest.mark.parametrize(
    "version", ["1.0", "1.2.3.dev1+ge871260", "1.2.3.dev15+ge871260.d20180625", "2345"]
)
def test_pretended(version: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(setuptools_scm.PRETEND_KEY, version)
    assert setuptools_scm.get_version() == version


def test_root_relative_to(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tmp_path.joinpath("setup.cfg").touch()
    assert_root(monkeypatch, str(tmp_path / "alt"))
    module = tmp_path / "module/file.py"
    module.parent.mkdir()
    module.touch()

    setuptools_scm.get_version(
        root="../alt",
        relative_to=str(module),
    )
    with pytest.warns(UserWarning, match="relative_to is expected to be a file.*"):
        setuptools_scm.get_version(
            root="../alt",
            relative_to=str(module.parent),
        )


def test_dump_version(tmp_path: Path) -> None:

    dump_version(tmp_path, "1.0", "first.txt")

    def read(name: str) -> str:
        return tmp_path.joinpath(name).read_text()

    assert read("first.txt") == "1.0"

    dump_version(tmp_path, "1.0.dev42", "first.py")
    lines = read("first.py").splitlines()
    assert "__version__ = version = '1.0.dev42'" in lines
    assert "__version_tuple__ = version_tuple = (1, 0, 'dev42')" in lines

    dump_version(tmp_path, "1.0.1+g4ac9d2c", "second.py")
    lines = read("second.py").splitlines()
    assert "__version__ = version = '1.0.1+g4ac9d2c'" in lines
    assert "__version_tuple__ = version_tuple = (1, 0, 1, 'g4ac9d2c')" in lines

    dump_version(tmp_path, "1.2.3.dev18+gb366d8b.d20210415", "third.py")
    lines = read("third.py").splitlines()
    assert "__version__ = version = '1.2.3.dev18+gb366d8b.d20210415'" in lines
    assert (
        "__version_tuple__ = version_tuple = (1, 2, 3, 'dev18', 'gb366d8b.d20210415')"
        in lines
    )

    import ast

    ast.parse(read("third.py"))


def test_parse_plain_fails(recwarn: pytest.WarningsRecorder) -> None:
    def parse(root: object) -> str:
        return "tricked you"

    with pytest.raises(TypeError):
        setuptools_scm.get_version(parse=parse)


def test_custom_version_cls() -> None:
    """Test that `normalize` and `version_cls` work as expected"""

    class MyVersion:
        def __init__(self, tag_str: str):
            self.version = tag_str

        def __repr__(self) -> str:
            return f"hello,{self.version}"

    # you can not use normalize=False and version_cls at the same time
    with pytest.raises(ValueError):
        setuptools_scm.get_version(normalize=False, version_cls=MyVersion)

    # TODO unfortunately with PRETEND_KEY the preformatted flag becomes True
    #  which bypasses our class. which other mechanism would be ok to use here
    #  to create a test?
    # monkeypatch.setenv(setuptools_scm.PRETEND_KEY, "1.0.1")
    # assert setuptools_scm.get_version(version_cls=MyVersion) == "1"
