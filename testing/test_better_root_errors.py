"""
Tests for better error messages when relative_to is not set.

This addresses the issue #279 where error messages should be more helpful
when setuptools-scm fails to detect a version but a repository exists
in a parent directory.
"""

from __future__ import annotations

import pytest

from setuptools_scm import Configuration
from setuptools_scm import get_version
from setuptools_scm._get_version_impl import _find_scm_in_parents
from setuptools_scm._get_version_impl import _version_missing
from testing.wd_wrapper import WorkDir


def setup_git_repo(wd: WorkDir) -> WorkDir:
    """Set up a git repository for testing."""
    wd("git init")
    wd("git config user.email test@example.com")
    wd('git config user.name "a test"')
    wd.add_command = "git add ."
    wd.commit_command = "git commit -m test-{reason}"
    return wd


def setup_hg_repo(wd: WorkDir) -> WorkDir:
    """Set up a mercurial repository for testing."""
    try:
        wd("hg init")
        wd.add_command = "hg add ."
        wd.commit_command = 'hg commit -m test-{reason} -u test -d "0 0"'
        return wd
    except Exception:
        pytest.skip("hg not available")


def test_find_scm_in_parents_finds_git(wd: WorkDir) -> None:
    """Test that _find_scm_in_parents correctly finds git repositories in parent directories."""
    # Set up git repo in root
    setup_git_repo(wd)

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
    setup_hg_repo(wd)

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
    setup_git_repo(wd)

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
    setup_git_repo(wd)

    # Create a subdirectory structure
    subdir = wd.cwd / "subproject" / "nested"
    subdir.mkdir(parents=True)

    # Create a dummy file to use as relative_to
    dummy_file = subdir / "setup.py"
    dummy_file.write_text("# dummy file")

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
    setup_git_repo(wd)
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
    setup_git_repo(wd)

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
