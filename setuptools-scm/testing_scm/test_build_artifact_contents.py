"""Built artifacts must carry the checkout's tracked files (#1540).

Every other test around file discovery asserts on warnings or on the
return value of ``find_files``.  None of them opened a built sdist or
wheel, which is why a pretended version silently dropped every tracked
file through three releases.

The fixture deliberately tracks a non-Python file.  setuptools' own
package discovery picks up ``*.py`` under a declared package, so a
``.py`` file reaches the artifact whether or not file discovery ran and
cannot tell the two apart.
"""

from __future__ import annotations

import sys
import tarfile
import zipfile

from pathlib import Path
from textwrap import dedent

import pytest

from vcs_versioning._run_cmd import run
from vcs_versioning.test_api import WorkDir

TRACKED_DATA = "demo_pkg/data.txt"
"""Tracked, and reachable only through the file finders."""

PYPROJECT = dedent("""\
    [build-system]
    requires = ["setuptools>=61", "setuptools-scm"]
    build-backend = "setuptools.build_meta"

    [project]
    name = "demo-pkg"
    dynamic = ["version"]

    [tool.setuptools]
    packages = ["demo_pkg"]

    [tool.setuptools_scm]
    %s
""")


def _write_project(wd: WorkDir, extra_config: str = "") -> None:
    wd.write("pyproject.toml", PYPROJECT % extra_config)
    wd.write("demo_pkg/__init__.py", "")
    wd.write(TRACKED_DATA, "payload\n")


def _build(cwd: Path) -> tuple[set[str], set[str]]:
    """Build an sdist and a wheel in a subprocess, return their members.

    Names are returned without the leading ``<name>-<version>/`` of the
    sdist, so both sets are keyed the same way as the project tree.
    """
    code = dedent("""\
        from setuptools import build_meta
        print("SDIST", build_meta.build_sdist("dist"))
        print("WHEEL", build_meta.build_wheel("dist"))
    """)
    dist = cwd / "dist"
    dist.mkdir(exist_ok=True)
    result = run([sys.executable, "-c", code], cwd)
    assert result.returncode == 0, (
        f"build failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )

    names: dict[str, str] = {}
    for line in result.stdout.splitlines():
        kind, _, name = line.partition(" ")
        if kind in ("SDIST", "WHEEL"):
            names[kind] = name

    with tarfile.open(dist / names["SDIST"]) as tar:
        sdist = {member.name.partition("/")[2] for member in tar.getmembers()}
    with zipfile.ZipFile(dist / names["WHEEL"]) as whl:
        wheel = set(whl.namelist())
    return sdist - {""}, wheel


@pytest.mark.issue(1540)
@pytest.mark.parametrize(
    "pretend_var",
    [
        None,
        "SETUPTOOLS_SCM_PRETEND_VERSION",
        "SETUPTOOLS_SCM_PRETEND_VERSION_FOR_DEMO_PKG",
    ],
    ids=["from-tag", "pretend", "pretend-scoped"],
)
def test_tracked_file_reaches_artifacts(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch, pretend_var: str | None
) -> None:
    """A pretended version says nothing about which files the checkout tracks."""
    wd.setup_git(monkeypatch)
    _write_project(wd)
    wd.add_and_commit()
    wd.create_tag("v1.0.0")
    if pretend_var is not None:
        monkeypatch.setenv(pretend_var, "9.9.9")

    sdist, wheel = _build(wd.cwd)

    assert TRACKED_DATA in sdist
    assert TRACKED_DATA in wheel


@pytest.mark.issue(1540)
def test_pretend_version_writes_file_list_but_not_version(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The two egg-info metadata files answer different questions.

    The file list describes the checkout, which a pretended version does
    not change.  ``scm_version.json`` describes what the SCM said, which a
    pretended version must not be passed off as.
    """
    wd.setup_git(monkeypatch)
    _write_project(wd)
    wd.add_and_commit()
    wd.create_tag("v1.0.0")
    monkeypatch.setenv("SETUPTOOLS_SCM_PRETEND_VERSION", "9.9.9")

    sdist, _ = _build(wd.cwd)

    assert "demo_pkg.egg-info/scm_file_list.json" in sdist
    assert "demo_pkg.egg-info/scm_version.json" not in sdist


@pytest.mark.issue(1540)
def test_tag_build_writes_both_metadata_files(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    wd.setup_git(monkeypatch)
    _write_project(wd)
    wd.add_and_commit()
    wd.create_tag("v1.0.0")

    sdist, _ = _build(wd.cwd)

    assert "demo_pkg.egg-info/scm_file_list.json" in sdist
    assert "demo_pkg.egg-info/scm_version.json" in sdist


@pytest.mark.issue(1212)
def test_no_checkout_keeps_finders_suppressed(wd: WorkDir) -> None:
    """Discovery that genuinely finds nothing must still skip the finders.

    This is the behaviour #1212 asked for, and the #1540 fix must not
    trade it away: with no checkout there is nothing to list, and probing
    every backend for one is what broke unrelated builds.
    """
    _write_project(wd, extra_config='fallback_version = "0.0.1"')

    sdist, _ = _build(wd.cwd)

    assert TRACKED_DATA not in sdist
    assert "demo_pkg/__init__.py" in sdist


@pytest.mark.issue(1540)
def test_pretend_version_defers_discovery_until_files_are_wanted(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Laziness is the point, but it has to be invisible from outside.

    A pretended version answers without discovering a checkout, because
    most builds only ever want a version.  The moment something asks for
    the workdir -- which only the file-listing consumers do -- discovery
    runs, once.
    """
    from setuptools_scm._integration.version_inference import infer_version_with_config
    from vcs_versioning import Configuration
    from vcs_versioning._pyproject_reading import read_pyproject

    wd.setup_git(monkeypatch)
    _write_project(wd)
    wd.add_and_commit()
    wd.create_tag("v1.0.0")
    monkeypatch.chdir(wd.cwd)
    monkeypatch.setenv("SETUPTOOLS_SCM_PRETEND_VERSION", "9.9.9")
    monkeypatch.setenv("SETUPTOOLS_SCM_WRITE_TO_SOURCE", "0")

    calls = 0
    real = Configuration.discover_workdir

    def counting(self: Configuration) -> object:
        nonlocal calls
        calls += 1
        return real(self)

    monkeypatch.setattr(Configuration, "discover_workdir", counting)

    data = infer_version_with_config(
        "demo-pkg", read_pyproject(path=wd.cwd / "pyproject.toml")
    )

    assert data.version == "9.9.9"
    assert calls == 0, "a pretended version must not pay for discovery"

    assert data.workdir is not None
    assert calls == 1, "asking for the workdir is what triggers discovery"

    assert data.workdir is not None
    assert calls == 1, "the answer is memoized"
