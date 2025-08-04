from __future__ import annotations

import logging

import pytest

from setuptools_scm._overrides import _find_close_env_var_matches
from setuptools_scm._overrides import _search_env_vars_with_prefix
from setuptools_scm._overrides import read_named_env


class TestSearchEnvVarsWithPrefix:
    """Test the _search_env_vars_with_prefix helper function."""

    def test_exact_match(self) -> None:
        """Test finding exact normalized matches."""
        env = {"SETUPTOOLS_SCM_TEST_FOR_MY_PACKAGE": "value1"}

        matches = _search_env_vars_with_prefix(
            "SETUPTOOLS_SCM_TEST_FOR_", "my-package", env
        )

        assert len(matches) == 1
        assert matches[0] == ("SETUPTOOLS_SCM_TEST_FOR_MY_PACKAGE", "value1")

    def test_multiple_normalizations(self) -> None:
        """Test finding various normalization patterns."""
        # Set up different normalization patterns
        env = {
            "SETUPTOOLS_SCM_TEST_FOR_MY_AWESOME_PKG": "value1",
            "SETUPTOOLS_SCM_TEST_FOR_MYAWESOMEPKG": "value2",
            "SETUPTOOLS_SCM_TEST_FOR_MY_AWESOME-PKG": "value3",  # duplicate
        }

        matches = _search_env_vars_with_prefix(
            "SETUPTOOLS_SCM_TEST_FOR_", "my-awesome.pkg", env
        )

        # Should find the variants that match our normalization patterns
        assert len(matches) >= 1
        env_vars = [var for var, _ in matches]
        assert "SETUPTOOLS_SCM_TEST_FOR_MY_AWESOME_PKG" in env_vars

    def test_no_matches(self) -> None:
        """Test when no matches are found."""
        # Set up unrelated env vars
        env = {
            "OTHER_VAR": "value",
            "SETUPTOOLS_SCM_OTHER_FOR_SOMETHING": "value",
        }

        matches = _search_env_vars_with_prefix(
            "SETUPTOOLS_SCM_TEST_FOR_", "nonexistent", env
        )

        assert len(matches) == 0

    def test_case_variations(self) -> None:
        """Test that case variations are handled."""
        env = {"SETUPTOOLS_SCM_TEST_FOR_MYPACKAGE": "value1"}

        matches = _search_env_vars_with_prefix(
            "SETUPTOOLS_SCM_TEST_FOR_", "MyPackage", env
        )

        assert len(matches) == 1
        assert matches[0][1] == "value1"


class TestFindCloseEnvVarMatches:
    """Test the _find_close_env_var_matches helper function."""

    def test_close_matches(self) -> None:
        """Test finding close matches for potential typos."""
        env = {
            "SETUPTOOLS_SCM_TEST_FOR_MY_PACKAG": "typo1",  # missing 'e'
            "SETUPTOOLS_SCM_TEST_FOR_MY_PAKAGE": "typo2",  # 'c' -> 'k'
            "SETUPTOOLS_SCM_TEST_FOR_OTHER_PKG": "unrelated",
        }

        close_matches = _find_close_env_var_matches(
            "SETUPTOOLS_SCM_TEST_FOR_", "MY_PACKAGE", env
        )

        # Should find the close matches but not the unrelated one
        assert "SETUPTOOLS_SCM_TEST_FOR_MY_PACKAG" in close_matches
        assert "SETUPTOOLS_SCM_TEST_FOR_MY_PAKAGE" in close_matches
        assert "SETUPTOOLS_SCM_TEST_FOR_OTHER_PKG" not in close_matches

    def test_threshold(self) -> None:
        """Test that threshold filtering works."""
        env = {"SETUPTOOLS_SCM_TEST_FOR_COMPLETELY_DIFFERENT": "unrelated"}

        close_matches = _find_close_env_var_matches(
            "SETUPTOOLS_SCM_TEST_FOR_", "MY_PACKAGE", env, threshold=0.8
        )

        # With high threshold, completely different string shouldn't match
        assert len(close_matches) == 0

    def test_no_close_matches(self) -> None:
        """Test when no close matches exist."""
        env: dict[str, str] = {}
        close_matches = _find_close_env_var_matches(
            "SETUPTOOLS_SCM_TEST_FOR_", "MY_PACKAGE", env
        )

        assert len(close_matches) == 0


class TestReadNamedEnvEnhanced:
    """Test the enhanced read_named_env function."""

    def test_standard_behavior_unchanged(self) -> None:
        """Test that standard behavior still works."""
        # Generic env var
        env = {"SETUPTOOLS_SCM_TEST": "generic_value"}
        assert read_named_env(name="TEST", dist_name=None, env=env) == "generic_value"

        # Dist-specific env var (standard normalization)
        env = {"SETUPTOOLS_SCM_TEST_FOR_MY_PACKAGE": "specific_value"}
        assert (
            read_named_env(name="TEST", dist_name="my-package", env=env)
            == "specific_value"
        )

    def test_alternative_normalization_found(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test finding alternative normalizations with warnings."""
        # Set up an alternative normalization pattern (user uses dots instead of canonical hyphens)
        env = {"SETUPTOOLS_SCM_TEST_FOR_MY.PACKAGE": "alt_value"}

        with caplog.at_level(logging.WARNING):
            result = read_named_env(name="TEST", dist_name="my.package", env=env)

        assert result == "alt_value"
        assert "Found environment variable" in caplog.text
        assert "but expected" in caplog.text

    def test_multiple_alternatives_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test warning when multiple alternative normalizations exist."""
        # Set up multiple alternatives that represent the same canonical package name
        # but use different normalizations in the env var
        env = {
            "SETUPTOOLS_SCM_TEST_FOR_MY.PACKAGE": "alt1",  # dots instead of hyphens
            "SETUPTOOLS_SCM_TEST_FOR_MY-PACKAGE": "alt2",  # dashes instead of underscores
            "SETUPTOOLS_SCM_TEST_FOR_my.package": "alt3",  # lowercase
        }

        with caplog.at_level(logging.WARNING):
            result = read_named_env(name="TEST", dist_name="my.package", env=env)

        assert result in ["alt1", "alt2", "alt3"]  # Should use one of them
        assert "Multiple alternative environment variables found" in caplog.text

    def test_typo_suggestions(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test suggestions for potential typos."""
        # Set up a close but not exact match
        env = {"SETUPTOOLS_SCM_TEST_FOR_MY_PACKAG": "typo_value"}

        with caplog.at_level(logging.WARNING):
            result = read_named_env(name="TEST", dist_name="my-package", env=env)

        # Should return None (generic fallback) but warn about close matches
        assert result is None
        assert "Did you mean one of these?" in caplog.text
        assert "SETUPTOOLS_SCM_TEST_FOR_MY_PACKAG" in caplog.text

    def test_fallback_to_generic(self) -> None:
        """Test fallback to generic env var when dist-specific not found."""
        env = {"SETUPTOOLS_SCM_TEST": "generic_fallback"}

        result = read_named_env(name="TEST", dist_name="nonexistent-package", env=env)

        assert result == "generic_fallback"

    def test_no_generic_fallback(self) -> None:
        """Test behavior when neither dist-specific nor generic env vars exist."""
        env: dict[str, str] = {}
        result = read_named_env(name="TEST", dist_name="some-package", env=env)

        assert result is None

    def test_dist_specific_overrides_generic(self) -> None:
        """Test that dist-specific env vars override generic ones."""
        env = {
            "SETUPTOOLS_SCM_TEST": "generic",
            "SETUPTOOLS_SCM_TEST_FOR_MY_PACKAGE": "specific",
        }

        result = read_named_env(name="TEST", dist_name="my-package", env=env)

        assert result == "specific"

    def test_custom_tool_prefix(self) -> None:
        """Test that custom tool prefixes work."""
        env = {"CUSTOM_TOOL_TEST_FOR_MY_PACKAGE": "custom_value"}

        result = read_named_env(
            tool="CUSTOM_TOOL", name="TEST", dist_name="my-package", env=env
        )

        assert result == "custom_value"

    def test_complex_dist_name_normalization(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test complex dist name normalization scenarios."""
        # User uses a non-canonical format (keeping underscores instead of canonical hyphens)
        # The canonical form of "complex.dist-name_with.dots" is "complex-dist-name-with-dots"
        # which becomes "COMPLEX_DIST_NAME_WITH_DOTS" as env var
        # But user set it with mixed format:
        env = {"SETUPTOOLS_SCM_TEST_FOR_COMPLEX.DIST_NAME_WITH.DOTS": "value"}

        with caplog.at_level(logging.WARNING):
            result = read_named_env(
                name="TEST", dist_name="complex.dist-name_with.dots", env=env
            )

        assert result == "value"
        assert "Found environment variable" in caplog.text

    def test_lowercase_environment_variable(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that lowercase environment variables are found as alternatives."""
        env = {"SETUPTOOLS_SCM_TEST_FOR_my.package": "lowercase_value"}

        with caplog.at_level(logging.WARNING):
            result = read_named_env(name="TEST", dist_name="my.package", env=env)

        assert result == "lowercase_value"
        assert "Found environment variable" in caplog.text
        assert "but expected" in caplog.text

    def test_edge_case_empty_dist_name(self) -> None:
        """Test edge case with empty dist name."""
        env = {"SETUPTOOLS_SCM_TEST": "generic"}

        result = read_named_env(name="TEST", dist_name="", env=env)

        # Should still try dist-specific lookup but fall back to generic
        assert result == "generic"
