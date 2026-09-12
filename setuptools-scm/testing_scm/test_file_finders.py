"""Deprecation of the global ``setuptools.file_finders`` entry point (#1407).

The warning lives on the setuptools-scm wrapper rather than in
``vcs_versioning``: reaching that module *is* the signal that setuptools
invoked the global file finder, so nothing has to sniff the project
layout to tell it apart from a library calling ``vcs_versioning``
directly.

A configured project never reaches it -- ``ScmEggInfoMixin`` lists files
from the discovered workdir, and when discovery found no workdir it says
so via ``scm_search_known_failed()``.
"""

from __future__ import annotations

import sys
import warnings

from pathlib import Path
from textwrap import dedent

import pytest

from setuptools_scm._integration.file_finders import find_files
from vcs_versioning._file_finders import scm_search_known_failed
from vcs_versioning._run_cmd import run
from vcs_versioning.test_api import WorkDir

_DEPRECATION = "setuptools.file_finders"


@pytest.mark.issue(1407)
def test_entry_point_warns(tmp_path: Path) -> None:
    """Reaching the entry point at all is what the deprecation is about."""
    with pytest.warns(DeprecationWarning, match=_DEPRECATION):
        find_files(str(tmp_path))


@pytest.mark.issue(1407)
def test_no_warn_when_scm_search_known_failed(tmp_path: Path) -> None:
    """A configured project that already ran discovery must stay quiet."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with scm_search_known_failed():
            find_files(str(tmp_path))
    assert [w for w in caught if _DEPRECATION in str(w.message)] == []


def _build_sdist(cwd: Path) -> str:
    """Build an sdist in-process and return the combined output."""
    code = dedent("""\
        import warnings
        from setuptools import build_meta
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            build_meta.build_sdist("dist")
        for w in caught:
            print("WARNING:", w.message)
    """)
    (cwd / "dist").mkdir(exist_ok=True)
    return run([sys.executable, "-c", code], cwd).stdout


@pytest.mark.issue(1407)
def test_unconfigured_build_warns(wd: WorkDir, monkeypatch: pytest.MonkeyPatch) -> None:
    """setuptools-scm as a bare build dependency warns on a real build."""
    wd.setup_git(monkeypatch)
    wd.cwd.joinpath("pyproject.toml").write_text(
        dedent("""\
            [build-system]
            requires = ["setuptools>=61", "setuptools-scm"]
            build-backend = "setuptools.build_meta"

            [project]
            name = "unconfigured"
            version = "1.0.0"
        """),
        encoding="utf-8",
    )
    wd.cwd.joinpath("mod.py").touch()
    wd.add_and_commit()

    assert _DEPRECATION in _build_sdist(wd.cwd)


@pytest.mark.issue(1407)
def test_configured_build_does_not_warn(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A configured project lists files from the workdir and stays quiet."""
    wd.setup_git(monkeypatch)
    wd.cwd.joinpath("pyproject.toml").write_text(
        dedent("""\
            [build-system]
            requires = ["setuptools>=61", "setuptools-scm"]
            build-backend = "setuptools.build_meta"

            [project]
            name = "configured"
            dynamic = ["version"]

            [tool.setuptools_scm]
        """),
        encoding="utf-8",
    )
    wd.cwd.joinpath("mod.py").touch()
    wd.add_and_commit()
    wd.create_tag("v1.0")

    assert _DEPRECATION not in _build_sdist(wd.cwd)
