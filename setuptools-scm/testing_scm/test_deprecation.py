"""Test deprecation warnings and their exact text."""

from pathlib import Path

import pytest

from setuptools_scm._integration.deprecation import warn_dynamic_version


def test_warn_dynamic_version_full_text() -> None:
    """Test the complete warning text for warn_dynamic_version function."""
    test_path = Path("test_file.toml")
    expected_warning = (
        f"{test_path}: at [test.section]\n"
        "test_expression is forcing setuptools to override the version setuptools-scm did already set\n"
        "When using setuptools-scm it's invalid to use setuptools dynamic version as well, please remove it.\n"
        "Setuptools-scm is responsible for setting the version, forcing setuptools to override creates errors."
    )

    with pytest.warns(UserWarning) as warning_info:  # noqa: PT030
        warn_dynamic_version(test_path, "test.section", "test_expression")

    assert len(warning_info) == 1
    assert str(warning_info[0].message) == expected_warning
