from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import pytest

import setuptools_scm
from setuptools_scm import Configuration
from setuptools_scm import dump_version
from setuptools_scm._run_cmd import run
from setuptools_scm.integration import data_from_mime
from setuptools_scm.version import meta
from setuptools_scm.version import ScmVersion
from testing.wd_wrapper import WorkDir


c = Configuration()

template = """\
__version__ = version = {version!r}
__version_tuple__ = version_tuple = {version_tuple!r}
__sha__ = {scm_version.node!r}
"""


def test_run_plain(tmp_path: Path) -> None:
    run([sys.executable, "-c", "print(1)"], cwd=tmp_path)


def test_data_from_mime(tmp_path: Path) -> None:
    tmpfile = tmp_path.joinpath("test.archival")
    tmpfile.write_text("name: test\nrevision: 1")

    res = data_from_mime(str(tmpfile))
    assert res == {"name": "test", "revision": "1"}


def test_version_from_pkginfo(wd: WorkDir) -> None:
    wd.write("PKG-INFO", "Version: 0.1")

    assert wd.get_version() == "0.1"

    # replicate issue 167
    assert wd.get_version(version_scheme="1.{0.distance}.0".format) == "0.1"


def assert_root(monkeypatch: pytest.MonkeyPatch, expected_root: str) -> None:
    """
    Patch version_from_scm to simply assert that root is expected root
    """

    def assertion(config: Configuration) -> ScmVersion:
        assert config.absolute_root == expected_root
        return ScmVersion("1.0", config=config)

    monkeypatch.setattr(setuptools_scm._get_version_impl, "parse_version", assertion)


def test_root_parameter_creation(monkeypatch: pytest.MonkeyPatch) -> None:
    assert_root(monkeypatch, os.getcwd())
    setuptools_scm.get_version()


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
    res = run([sys.executable, "setup.py", "--version"], p)
    assert res.stdout == "12.34"


def test_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")
    p = tmp_path / "sub/package"
    p.mkdir(parents=True)
    p.joinpath("setup.py").write_text(
        """from setuptools import setup
setup(use_scm_version={"fallback_version": "12.34"})
"""
    )
    res = run([sys.executable, "setup.py", "--version"], p)
    assert res.stdout == "12.34"


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
    res = run([sys.executable, "setup.py", "--version"], p)
    assert res.stdout == "12.34"


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
    res = run([sys.executable, "setup.py", "--version"], p)
    assert res.stdout == "12.34"


def test_get_version_blank_tag_regex() -> None:
    with pytest.warns(
        DeprecationWarning, match="empty regex for tag regex is invalid, using default"
    ):
        setuptools_scm.get_version(tag_regex="")


@pytest.mark.parametrize(
    "version", ["1.0", "1.2.3.dev1+ge871260", "1.2.3.dev15+ge871260.d20180625", "2345"]
)
def test_pretended(version: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(setuptools_scm._overrides.PRETEND_KEY, version)
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
    version = "1.0"
    scm_version = meta(version, config=c)
    dump_version(tmp_path, version, "first.txt", scm_version=scm_version)

    def read(name: str) -> str:
        return tmp_path.joinpath(name).read_text()

    assert read("first.txt") == "1.0"

    version = "1.0.dev42"
    scm_version = meta("1.0", distance=42, config=c)
    dump_version(tmp_path, version, "first.py", scm_version=scm_version)
    lines = read("first.py").splitlines()
    assert lines[-2:] == [
        "__version__ = version = '1.0.dev42'  # type: str",
        "__version_tuple__ = version_tuple = (1, 0, 'dev42')"
        "  # type: Tuple[int | str, ...]",
    ]

    version = "1.0.1+g4ac9d2c"
    scm_version = meta("1.0.1", node="g4ac9d2c", config=c)
    dump_version(
        tmp_path, version, "second.py", scm_version=scm_version, template=template
    )
    lines = read("second.py").splitlines()
    assert "__version__ = version = '1.0.1+g4ac9d2c'" in lines
    assert "__version_tuple__ = version_tuple = (1, 0, 1, 'g4ac9d2c')" in lines
    assert "__sha__ = 'g4ac9d2c'" in lines

    version = "1.2.3.dev18+gb366d8b.d20210415"
    scm_version = meta(
        "1.2.3", node="gb366d8b", distance=18, node_date=date(2021, 4, 15), config=c
    )
    dump_version(
        tmp_path, version, "third.py", scm_version=scm_version, template=template
    )
    lines = read("third.py").splitlines()
    assert "__version__ = version = '1.2.3.dev18+gb366d8b.d20210415'" in lines
    assert (
        "__version_tuple__ = version_tuple = (1, 2, 3, 'dev18', 'gb366d8b.d20210415')"
        in lines
    )
    assert "__sha__ = 'gb366d8b'" in lines

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


def test_internal_get_version_warns_for_version_files(tmp_path: Path) -> None:
    tmp_path.joinpath("PKG-INFO").write_text("Version: 0.1")
    c = Configuration(root=tmp_path, fallback_root=tmp_path)
    with pytest.warns(
        DeprecationWarning,
        match="force_write_version_files ought to be set,"
        " presuming the legacy True value",
    ):
        ver = setuptools_scm._get_version(c)
    assert ver == "0.1"

    # force write won't write as no version file is configured
    assert setuptools_scm._get_version(c, force_write_version_files=False) == ver

    assert setuptools_scm._get_version(c, force_write_version_files=True) == ver
