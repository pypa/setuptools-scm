"""
Tests for better error messages when relative_to is not set.

This addresses the issue #279 where error messages should be more helpful
when setuptools-scm fails to detect a version but a repository exists
in a parent directory.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from vcs_versioning import Configuration
from vcs_versioning._environment import VcsEnvironment
from vcs_versioning._get_version_impl import (
    _find_scm_in_parents,
    _version_missing,
    get_version,
)
from vcs_versioning._overrides import _read_pretended_version_for
from vcs_versioning.test_api import WorkDir

# No longer need to import setup functions - using WorkDir methods directly


def test_find_scm_in_parents_finds_git(wd: WorkDir) -> None:
    """Test that _find_scm_in_parents correctly finds git repositories in parent directories."""
    # Set up git repo in root
    wd.setup_git()

    # Create a subdirectory structure
    subdir = wd.cwd / "subproject" / "nested"
    subdir.mkdir(parents=True)

    # Test from the nested subdirectory
    config = Configuration(root=str(subdir))
    found_scm = _find_scm_in_parents(config)

    assert found_scm == wd.cwd


def test_find_scm_in_parents_finds_hg(wd: WorkDir) -> None:
    """Test that _find_scm_in_parents correctly finds mercurial repositories in parent directories."""
    # Set up hg repo in root
    wd.setup_hg()

    # Create a subdirectory structure
    subdir = wd.cwd / "subproject" / "nested"
    subdir.mkdir(parents=True)

    # Test from the nested subdirectory
    config = Configuration(root=str(subdir))
    found_scm = _find_scm_in_parents(config)

    assert found_scm == wd.cwd


def test_find_scm_in_parents_returns_none(wd: WorkDir) -> None:
    """Test that _find_scm_in_parents returns None when no SCM repository is found."""
    # Don't initialize any SCM, just create subdirectories
    subdir = wd.cwd / "project" / "nested"
    subdir.mkdir(parents=True)

    config = Configuration(root=str(subdir))
    found_scm = _find_scm_in_parents(config)

    assert found_scm is None


def test_version_missing_with_scm_in_parent(wd: WorkDir) -> None:
    """Test that _version_missing provides helpful error message when SCM is found in parent."""
    # Set up git repo in root
    wd.setup_git()

    # Create a subdirectory structure
    subdir = wd.cwd / "subproject" / "nested"
    subdir.mkdir(parents=True)

    # Test error message when relative_to is not set
    config = Configuration(root=str(subdir), relative_to=None)

    with pytest.raises(LookupError) as exc_info:
        _version_missing(config)

    error_message = str(exc_info.value)

    # Check that the error message mentions the parent repository
    assert f"repository was found in a parent directory: {wd.cwd}" in error_message
    assert "relative_to" in error_message
    assert "search_parent_directories = true" in error_message
    assert "setuptools_scm.get_version(relative_to=__file__)" in error_message


def test_version_missing_no_scm_found(wd: WorkDir) -> None:
    """Test that _version_missing provides standard error message when no SCM is found anywhere."""
    # Don't initialize any SCM, just create subdirectories
    subdir = wd.cwd / "project" / "nested"
    subdir.mkdir(parents=True)

    config = Configuration(root=str(subdir), relative_to=None)

    with pytest.raises(LookupError) as exc_info:
        _version_missing(config)

    error_message = str(exc_info.value)

    # Check that it falls back to the standard error message
    assert (
        "Make sure you're either building from a fully intact git repository"
        in error_message
    )
    assert "repository was found in a parent directory" not in error_message


def test_version_missing_with_relative_to_set(wd: WorkDir) -> None:
    """Test that when relative_to is set, we don't search parents for error messages."""
    # Set up git repo in root
    wd.setup_git()

    # Create a subdirectory structure
    subdir = wd.cwd / "subproject" / "nested"
    subdir.mkdir(parents=True)

    # Create a dummy file to use as relative_to
    dummy_file = subdir / "setup.py"
    dummy_file.write_text("# dummy file", encoding="utf-8")

    # Test error message when relative_to IS set
    config = Configuration(root=str(subdir), relative_to=str(dummy_file))

    with pytest.raises(LookupError) as exc_info:
        _version_missing(config)

    error_message = str(exc_info.value)

    # Should not mention parent directory when relative_to is set
    assert "repository was found in a parent directory" not in error_message
    assert (
        "Make sure you're either building from a fully intact git repository"
        in error_message
    )


def test_search_parent_directories_works_as_suggested(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that the suggested search_parent_directories=True solution actually works."""
    # Set up git repo
    wd.setup_git()
    wd.commit_testfile()  # Make sure there's a commit for version detection

    # Create a subdirectory
    subdir = wd.cwd / "subproject"
    subdir.mkdir()

    # Change to the subdirectory
    monkeypatch.chdir(subdir)

    # This should work with search_parent_directories=True
    version = get_version(search_parent_directories=True)
    assert version is not None
    assert "0.1.dev" in version


def test_integration_better_error_from_nested_directory(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integration test: get_version from nested directory should give helpful error."""
    # Set up git repo
    wd.setup_git()

    # Create a subdirectory
    subdir = wd.cwd / "subproject"
    subdir.mkdir()

    # Change to the subdirectory
    monkeypatch.chdir(subdir)

    # Try to get version without any configuration
    with pytest.raises(LookupError) as exc_info:
        get_version()

    error_message = str(exc_info.value)

    # Should suggest helpful solutions
    assert f"repository was found in a parent directory: {wd.cwd}" in error_message
    assert "search_parent_directories = true" in error_message


def _suggested_pretend_vars(message: str) -> list[str]:
    return re.findall(
        r"\b([A-Z][A-Z_]*PRETEND_VERSION(?:_FOR_\S+?)?)(?=[,\s])", message
    )


@pytest.mark.parametrize("tool", ["SETUPTOOLS_SCM", "HATCH_VCS"])
def test_version_missing_suggests_usable_pretend_vars(
    tmp_path: Path, tool: str
) -> None:
    """Every env var the "no version found" error names must actually be read."""
    env = VcsEnvironment.from_env(tool, env={})
    config = Configuration(root=tmp_path, dist_name="My-Pkg.Name", _env=env)

    with pytest.raises(LookupError) as exc_info:
        _version_missing(config)

    message = str(exc_info.value)
    assert tool.lower().replace("_", "-") in message

    suggested = _suggested_pretend_vars(message)
    assert suggested, f"error suggests no env var: {message}"
    for name in suggested:
        pretended = _read_pretended_version_for(config, env={name: "1.2.3"})
        assert pretended is not None, f"{name} is suggested but not read"
        assert str(pretended.tag) == "1.2.3"


def test_version_missing_placeholder_names_are_usable(tmp_path: Path) -> None:
    """Without a dist name the message shows a placeholder that resolves correctly.

    Uses a bare vcs-versioning environment, where only ``VCS_VERSIONING_*``
    is read -- the case that used to be told to set ``SETUPTOOLS_SCM_*``.
    """
    env = VcsEnvironment.from_env(env={})
    config = Configuration(root=tmp_path, _env=env)

    with pytest.raises(LookupError) as exc_info:
        _version_missing(config)

    suggested = _suggested_pretend_vars(str(exc_info.value))
    assert suggested
    named_config = Configuration(root=tmp_path, dist_name="my-pkg", _env=env)
    for template in suggested:
        assert template.endswith("_FOR_${NORMALIZED_DIST_NAME}")
        name = template.replace("${NORMALIZED_DIST_NAME}", "MY_PKG")
        pretended = _read_pretended_version_for(named_config, env={name: "1.2.3"})
        assert pretended is not None, f"{name} is suggested but not read"
