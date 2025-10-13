"""Test the expect_parse and matches functionality."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from setuptools_scm import Configuration
from setuptools_scm.version import ScmVersion, meta
from vcs_versioning._version_schemes import mismatches
from vcs_versioning.test_api import TEST_SOURCE_DATE, WorkDir


def test_scm_version_matches_basic() -> None:
    """Test the ScmVersion.matches method with various combinations."""
    c = Configuration()

    # Create test version with all properties set
    version = meta(
        "1.2.3",
        distance=5,
        dirty=True,
        node="abc123def456",
        branch="main",
        config=c,
    )

    # Test individual matches
    assert version.matches(tag="1.2.3")
    assert version.matches(distance=5)
    assert version.matches(dirty=True)
    assert version.matches(branch="main")
    assert version.matches(exact=False)

    # Test combined matches
    assert version.matches(tag="1.2.3", distance=5, dirty=True, branch="main")

    # Test node prefix matching
    assert version.matches(node_prefix="a")
    assert version.matches(node_prefix="abc")
    assert version.matches(node_prefix="abc123")
    assert version.matches(node_prefix="abc123def456")

    # Test mismatches are falsy
    assert not version.matches(tag="1.2.4")
    assert not version.matches(node_prefix="xyz")
    assert not version.matches(distance=10)
    assert not version.matches(dirty=False)


def test_scm_version_matches_exact() -> None:
    """Test exact matching."""
    c = Configuration()

    # Exact version
    exact_version = meta("2.0.0", distance=0, dirty=False, config=c)
    assert exact_version.matches(exact=True)

    # Non-exact due to distance
    with_distance = meta("2.0.0", distance=1, dirty=False, config=c)
    assert not with_distance.matches(exact=True)

    # Non-exact due to dirty
    dirty_version = meta("2.0.0", distance=0, dirty=True, config=c)
    assert not dirty_version.matches(exact=True)


def test_expect_parse_calls_matches(tmp_path: Path) -> None:
    """Test that expect_parse correctly parses and calls matches."""
    wd = WorkDir(tmp_path)

    # Create a mock parse function that returns a predefined ScmVersion
    c = Configuration()
    mock_version = meta(
        "3.0.0",
        distance=2,
        dirty=False,
        node="fedcba987654",
        branch="develop",
        config=c,
    )

    def mock_parse(root: Path, config: Configuration) -> ScmVersion | None:
        return mock_version

    wd.parse = mock_parse

    # Test successful match
    wd.expect_parse(tag="3.0.0", distance=2, dirty=False)
    wd.expect_parse(node_prefix="fed")
    wd.expect_parse(branch="develop")

    # Test that mismatches raise AssertionError
    with pytest.raises(AssertionError, match="Version mismatch"):
        wd.expect_parse(tag="3.0.1")

    with pytest.raises(AssertionError, match="Version mismatch"):
        wd.expect_parse(dirty=True)

    with pytest.raises(AssertionError, match="Version mismatch"):
        wd.expect_parse(node_prefix="abc")


def test_expect_parse_without_parse_function(tmp_path: Path) -> None:
    """Test that expect_parse raises error when parse is not configured."""
    wd = WorkDir(tmp_path)

    with pytest.raises(RuntimeError, match="No SCM configured"):
        wd.expect_parse(tag="1.0.0")


def test_expect_parse_with_none_result(tmp_path: Path) -> None:
    """Test that expect_parse handles None result from parse."""
    wd = WorkDir(tmp_path)

    def mock_parse_none(root: Path, config: Configuration) -> ScmVersion | None:
        return None

    wd.parse = mock_parse_none

    with pytest.raises(AssertionError, match="Failed to parse version"):
        wd.expect_parse(tag="1.0.0")


def test_missmatches_string_formatting() -> None:
    """Test mismatches string representation for good error messages."""
    mismatch_obj = mismatches(
        expected={"tag": "1.0.0", "distance": 0, "dirty": False},
        actual={"tag": "2.0.0", "distance": 5, "dirty": True},
    )

    # Test that mismatches is falsy
    assert not mismatch_obj

    # Test string representation
    str_repr = str(mismatch_obj)
    assert "tag: expected '1.0.0', got '2.0.0'" in str_repr
    assert "distance: expected 0, got 5" in str_repr
    assert "dirty: expected False, got True" in str_repr


def test_missmatches_node_prefix_formatting() -> None:
    """Test mismatches formatting for node prefix mismatches."""
    mismatch_obj = mismatches(
        expected={"node_prefix": "abc"},
        actual={"node": "def123456"},
    )

    str_repr = str(mismatch_obj)
    assert "node: expected prefix 'abc', got 'def123456'" in str_repr


def test_scm_version_matches_datetime() -> None:
    """Test that ScmVersion.matches works with datetime fields."""
    c = Configuration()

    # Create version with specific datetime
    version = meta(
        "1.0.0",
        distance=0,
        dirty=False,
        node_date=date(2023, 6, 15),
        time=TEST_SOURCE_DATE,
        config=c,
    )

    # Test date matching
    assert version.matches(node_date=date(2023, 6, 15))
    assert not version.matches(node_date=date(2023, 6, 16))

    # Test time matching
    assert version.matches(time=TEST_SOURCE_DATE)
    assert not version.matches(time=datetime(2023, 1, 1, tzinfo=timezone.utc))
