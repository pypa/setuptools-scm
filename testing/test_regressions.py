from __future__ import annotations

import pprint
import subprocess
import sys
import textwrap

from dataclasses import replace
from importlib.metadata import EntryPoint
from importlib.metadata import distribution
from pathlib import Path

import pytest

from setuptools_scm import Configuration
from setuptools_scm._run_cmd import run
from setuptools_scm.git import parse
from setuptools_scm.integration import data_from_mime
from setuptools_scm.version import meta

from .wd_wrapper import WorkDir


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


def test_fallback_message(wd: WorkDir, monkeypatch: pytest.MonkeyPatch) -> None:
    """Check that no warning/error messages are normally outputted"""
    # setup a basic project that would not trigger any (other) warning/errors
    pyproject = """\
        [build-system]
        requires = ["setuptools", "setuptools_scm"]
        build-backend = "setuptools.build_meta"

        [project]
        name = "example"
        dynamic = ["version"]

        [tool.setuptools_scm]
        """
    git_archival = """\
        node: $Format:%H$
        node-date: $Format:%cI$
        describe-name: $Format:%(describe:tags=true,match=*[0-9]*)$
        """
    wd.write("pyproject.toml", textwrap.dedent(pyproject))
    wd.write(".git_archival.txt", textwrap.dedent(git_archival))
    wd.write(".gitattributes", ".git_archival.txt  export-subst")
    wd.write("README.md", "")
    wd("git init")
    wd("git config user.email user@host")
    wd("git config user.name user")
    wd.add_command = "git add ."
    wd.commit_command = "git commit -m test-{reason}"
    wd.add_and_commit()
    wd("git tag v0.1.0")
    version = wd.get_version()
    assert version == "0.1.0"

    # Run build and check messages
    monkeypatch.delenv("SETUPTOOLS_SCM_DEBUG")
    # with caplog.at_level(logging.WARN):
    res_build = subprocess.run(
        [sys.executable, "-m", "build", "-nx"],
        cwd=wd.cwd,
        capture_output=True,
    )
    assert res_build.returncode == 0
    # Maybe there is a cleaner way to use caplog?
    assert not res_build.stderr


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
        match=".*VERSION.py' .* .*subdir.*",
    ):
        write_version_files(replace(c, root=subdir), "1.0", v)
