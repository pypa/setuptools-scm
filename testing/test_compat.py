"""Test compatibility utilities."""

from __future__ import annotations

import pytest

from setuptools_scm._compat import normalize_path_for_assertion
from setuptools_scm._compat import strip_path_suffix


def test_normalize_path_for_assertion() -> None:
    """Test path normalization for assertions."""
    # Unix-style paths should remain unchanged
    assert normalize_path_for_assertion("/path/to/file") == "/path/to/file"

    # Windows-style paths should be normalized
    assert normalize_path_for_assertion(r"C:\path\to\file") == "C:/path/to/file"
    assert normalize_path_for_assertion(r"path\to\file") == "path/to/file"

    # Mixed paths should be normalized
    assert normalize_path_for_assertion(r"C:\path/to\file") == "C:/path/to/file"

    # Already normalized paths should remain unchanged
    assert normalize_path_for_assertion("path/to/file") == "path/to/file"


def test_strip_path_suffix_success() -> None:
    """Test successful path suffix stripping."""
    # Unix-style paths
    assert strip_path_suffix("/home/user/project", "project") == "/home/user/"
    assert (
        strip_path_suffix("/home/user/project/subdir", "project/subdir")
        == "/home/user/"
    )

    # Windows-style paths
    assert (
        strip_path_suffix("C:\\Users\\user\\project", "project") == "C:\\Users\\user\\"
    )
    assert (
        strip_path_suffix("C:\\Users\\user\\project\\subdir", "project/subdir")
        == "C:\\Users\\user\\"
    )

    # Mixed paths should work due to normalization
    assert (
        strip_path_suffix("C:\\Users\\user\\project", "project") == "C:\\Users\\user\\"
    )
    assert strip_path_suffix("/home/user/project", "project") == "/home/user/"

    # Edge cases
    assert strip_path_suffix("project", "project") == ""
    assert strip_path_suffix("/project", "project") == "/"


def test_strip_path_suffix_failure() -> None:
    """Test failed path suffix stripping."""
    with pytest.raises(AssertionError, match="Path assertion failed"):
        strip_path_suffix("/home/user/project", "other")

    with pytest.raises(AssertionError, match="Custom error"):
        strip_path_suffix("/home/user/project", "other", "Custom error")


def test_integration_example() -> None:
    """Test the integration pattern used in the codebase."""
    # Simulate the pattern used in git.py and _file_finders/git.py
    full_path = r"C:\\Users\\user\\project\\subdir"
    suffix = "subdir"

    # Now this is a single operation
    prefix = strip_path_suffix(full_path, suffix)
    assert prefix == r"C:\\Users\\user\\project\\"
