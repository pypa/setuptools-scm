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
    """Env var names the message offers -- ``_FOR_<DIST>`` is a placeholder, not one."""
    return re.findall(
        r"\b([A-Z][A-Z_]*PRETEND_VERSION(?:_FOR_[A-Z0-9_]+)?)(?=[,\s])", message
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


@pytest.mark.parametrize("tools", [("SETUPTOOLS_SCM",), ()])
def test_version_missing_without_dist_name_offers_only_generic_vars(
    tmp_path: Path, tools: tuple[str, ...]
) -> None:
    """Without a dist name the per-distribution form cannot match -- say so."""
    env = VcsEnvironment.from_env(*tools, env={})
    config = Configuration(root=tmp_path, _env=env)

    with pytest.raises(LookupError) as exc_info:
        _version_missing(config)

    message = str(exc_info.value)
    suggested = _suggested_pretend_vars(message)
    assert suggested == list(env.make_reader().candidate_names("PRETEND_VERSION"))

    for name in suggested:
        assert "_FOR_" not in name
        pretended = _read_pretended_version_for(config, env={name: "1.2.3"})
        assert pretended is not None, f"{name} is suggested but not read"

    assert "No distribution name is known here" in message
    assert f"{env.tool_names[0]}_PRETEND_VERSION_FOR_<DIST>" in message


@pytest.mark.parametrize(
    ("tools", "api_example"),
    [
        (("SETUPTOOLS_SCM",), "setuptools_scm.get_version(relative_to=__file__)"),
        ((), "vcs_versioning.get_version(relative_to=__file__)"),
    ],
)
def test_version_missing_offers_the_api_of_the_running_tool(
    wd: WorkDir, tools: tuple[str, ...], api_example: str
) -> None:
    """Known integrations get their own get_version() offered as option 1."""
    wd.setup_git()
    subdir = wd.cwd / "subproject" / "nested"
    subdir.mkdir(parents=True)

    env = VcsEnvironment.from_env(*tools, env={})
    config = Configuration(root=str(subdir), relative_to=None, _env=env)

    with pytest.raises(LookupError) as exc_info:
        _version_missing(config)

    message = str(exc_info.value)
    assert "1. Use the 'relative_to' parameter" in message
    assert api_example in message
    assert "4. Set the root explicitly" in message


@pytest.mark.issue(1550)
def test_version_missing_accepts_tool_from_older_setuptools_scm(
    tmp_path: Path,
) -> None:
    """setuptools-scm 10.1.0-10.2.3 pass tool= and accept any vcs-versioning<3."""
    env = VcsEnvironment.from_env("SETUPTOOLS_SCM", env={})
    config = Configuration(root=tmp_path, dist_name="demo-pkg", _env=env)

    with pytest.raises(LookupError, match="setuptools-scm was unable to detect"):
        _version_missing(config, tool=env.tool_names[0])


def test_version_missing_omits_api_example_for_third_party_tools(wd: WorkDir) -> None:
    """A third-party integrator has no get_version() here -- don't invent one."""
    wd.setup_git()
    subdir = wd.cwd / "subproject" / "nested"
    subdir.mkdir(parents=True)

    env = VcsEnvironment.from_env("HATCH_VCS", env={})
    config = Configuration(root=str(subdir), relative_to=None, _env=env)

    with pytest.raises(LookupError) as exc_info:
        _version_missing(config)

    message = str(exc_info.value)
    assert "get_version(relative_to=__file__)" not in message
    assert "relative_to" not in message
    # the remaining options are renumbered rather than starting at 2
    assert "1. Enable parent directory search" in message
    assert "3. Set the root explicitly" in message
