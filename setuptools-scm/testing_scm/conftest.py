"""Pytest configuration for setuptools_scm tests.

Uses vcs_versioning.test_api as a pytest plugin for common test infrastructure.
"""

from __future__ import annotations

import os

from pathlib import Path
from typing import Any

import pytest


# Re-export for convenience
from vcs_versioning.test_api import TEST_SOURCE_DATE
from vcs_versioning.test_api import TEST_SOURCE_DATE_EPOCH
from vcs_versioning.test_api import TEST_SOURCE_DATE_FORMATTED
from vcs_versioning.test_api import TEST_SOURCE_DATE_TIMESTAMP
from vcs_versioning.test_api import DebugMode
from vcs_versioning.test_api import WorkDir

# Use vcs_versioning test infrastructure as a pytest plugin
# Moved to pyproject.toml addopts to avoid non-top-level conftest issues
# pytest_plugins = ["vcs_versioning.test_api"]

__all__ = [
    "TEST_SOURCE_DATE",
    "TEST_SOURCE_DATE_EPOCH",
    "TEST_SOURCE_DATE_FORMATTED",
    "TEST_SOURCE_DATE_TIMESTAMP",
    "DebugMode",
    "WorkDir",
]


def pytest_configure(config: pytest.Config) -> None:
    """Additional configuration for setuptools_scm tests."""
    # Set both debug env vars for backward compatibility
    os.environ["SETUPTOOLS_SCM_DEBUG"] = "1"


VERSION_PKGS = [
    "setuptools",
    "setuptools_scm",
    "vcs-versioning",
    "packaging",
    "build",
    "wheel",
]


def pytest_report_header() -> list[str]:
    """Report package versions at test start."""
    from importlib.metadata import version

    res = []
    for pkg in VERSION_PKGS:
        try:
            pkg_version = version(pkg)
            module_name = pkg.replace("-", "_")
            path = __import__(module_name).__file__
            if path and "site-packages" in path:
                # Replace everything up to and including site-packages with site::
                parts = path.split("site-packages", 1)
                if len(parts) > 1:
                    path = "site::" + parts[1]
            elif path and str(Path.cwd()) in path:
                # Replace current working directory with CWD::
                path = path.replace(str(Path.cwd()), "CWD::")
            res.append(f"{pkg} version {pkg_version} from {path}")
        except Exception:
            pass
    return res


def pytest_addoption(parser: Any) -> None:
    """Add setuptools_scm-specific test options."""
    group = parser.getgroup("setuptools_scm")
    group.addoption(
        "--test-legacy", dest="scm_test_virtualenv", default=False, action="store_true"
    )
