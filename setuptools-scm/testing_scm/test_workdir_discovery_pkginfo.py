"""Tests for PKG-INFO discovery (depends on setuptools-scm entry points)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vcs_versioning._config import Configuration
from vcs_versioning._fallback_workdir import PkgInfoWorkdir
from vcs_versioning._worktree_discovery import discover_workdir


def test_discovers_pkginfo(tmp_path: Path) -> None:
    (tmp_path / "PKG-INFO").write_text(
        "Metadata-Version: 2.1\nName: pkg\nVersion: 3.0.0\n",
        encoding="utf-8",
    )
    config = Configuration(relative_to=str(tmp_path / "pyproject.toml"))
    result = discover_workdir(config)
    assert result is not None
    assert isinstance(result, PkgInfoWorkdir)


@pytest.mark.issue(1431)
def test_unprocessed_archival_falls_through_to_pkginfo(tmp_path: Path) -> None:
    """Unprocessed .git_archival.txt must not shadow a valid PKG-INFO.

    PyPI sdists contain both files: a .git_archival.txt with raw
    ``$Format:...`` placeholders (never substituted because the sdist
    was built by setuptools, not ``git archive``) and a PKG-INFO with
    the correct version.  Before the fix, the archival fallback was
    stashed as the sole candidate and its ``get_scm_version()`` returned
    None, causing a LookupError.
    """
    (tmp_path / ".git_archival.txt").write_text(
        "node: $Format:%H$\n"
        "node-date: $Format:%cI$\n"
        "describe-name: $Format:%(describe:tags=true)$\n"
        "ref-names: $Format:%D$\n",
        encoding="utf-8",
    )
    (tmp_path / "PKG-INFO").write_text(
        "Metadata-Version: 2.1\nName: my-pkg\nVersion: 1.2.3\n",
        encoding="utf-8",
    )
    config = Configuration(relative_to=str(tmp_path / "pyproject.toml"))
    result = discover_workdir(config)
    assert result is not None
    assert isinstance(result, PkgInfoWorkdir)
    version = result.get_scm_version()
    assert version is not None
    assert str(version.tag) == "1.2.3"
