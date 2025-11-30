"""Pytest configuration for vcs-versioning tests.

Uses vcs_versioning.test_api as a pytest plugin.
"""

from __future__ import annotations

# Use our own test_api module as a pytest plugin
# Moved to pyproject.toml addopts to avoid non-top-level conftest issues
# pytest_plugins = ["vcs_versioning.test_api"]
