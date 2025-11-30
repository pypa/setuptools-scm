"""Tests for GlobalOverrides API methods."""

from __future__ import annotations

import logging

import pytest
from vcs_versioning.overrides import GlobalOverrides


def test_from_active_modifies_field() -> None:
    """Test that from_active() creates a modified copy."""
    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "1"}):
        # Original has DEBUG level
        assert GlobalOverrides.from_active().debug == logging.DEBUG

        # Create modified version with INFO level
        with GlobalOverrides.from_active(debug=logging.INFO):
            from vcs_versioning.overrides import get_active_overrides

            active = get_active_overrides()
            assert active.debug == logging.INFO


def test_from_active_preserves_other_fields() -> None:
    """Test that from_active() preserves fields not explicitly changed."""
    env = {
        "TEST_DEBUG": "20",  # INFO
        "TEST_SUBPROCESS_TIMEOUT": "100",
        "TEST_HG_COMMAND": "custom_hg",
        "SOURCE_DATE_EPOCH": "1234567890",
    }

    with GlobalOverrides.from_env("TEST", env=env):
        # Modify only debug level
        with GlobalOverrides.from_active(debug=logging.WARNING):
            from vcs_versioning.overrides import get_active_overrides

            active = get_active_overrides()
            assert active.debug == logging.WARNING
            # Other fields preserved
            assert active.subprocess_timeout == 100
            assert active.hg_command == "custom_hg"
            assert active.source_date_epoch == 1234567890
            assert active.tool == "TEST"


def test_from_active_without_context_raises() -> None:
    """Test that from_active() raises when no context is active."""
    from vcs_versioning import overrides

    # Temporarily clear any active context
    token = overrides._active_overrides.set(None)
    try:
        with pytest.raises(
            RuntimeError,
            match="Cannot call from_active\\(\\) without an active GlobalOverrides context",
        ):
            GlobalOverrides.from_active(debug=logging.INFO)
    finally:
        overrides._active_overrides.reset(token)


def test_export_to_dict() -> None:
    """Test exporting overrides to a dictionary."""
    env_source = {
        "TEST_DEBUG": "INFO",
        "TEST_SUBPROCESS_TIMEOUT": "99",
        "TEST_HG_COMMAND": "/usr/bin/hg",
        "SOURCE_DATE_EPOCH": "1672531200",
    }

    overrides = GlobalOverrides.from_env("TEST", env=env_source)

    target_env: dict[str, str] = {}
    overrides.export(target_env)

    assert target_env["TEST_DEBUG"] == "20"  # INFO level
    assert target_env["TEST_SUBPROCESS_TIMEOUT"] == "99"
    assert target_env["TEST_HG_COMMAND"] == "/usr/bin/hg"
    assert target_env["SOURCE_DATE_EPOCH"] == "1672531200"


def test_export_to_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test exporting overrides via monkeypatch."""
    import os

    overrides = GlobalOverrides.from_env(
        "TEST",
        env={
            "TEST_DEBUG": "DEBUG",
            "TEST_SUBPROCESS_TIMEOUT": "77",
            "SOURCE_DATE_EPOCH": "1000000000",
        },
    )

    overrides.export(monkeypatch)

    # Check that environment was set
    assert os.environ["TEST_DEBUG"] == "10"  # DEBUG level
    assert os.environ["TEST_SUBPROCESS_TIMEOUT"] == "77"
    assert os.environ["SOURCE_DATE_EPOCH"] == "1000000000"


def test_export_debug_false() -> None:
    """Test that debug=False exports as '0'."""
    overrides = GlobalOverrides.from_env("TEST", env={})

    target_env: dict[str, str] = {}
    overrides.export(target_env)

    assert target_env["TEST_DEBUG"] == "0"


def test_from_active_and_export_together(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test using from_active() and export() together."""
    import os

    # Start with one context
    with GlobalOverrides.from_env("TOOL", env={"TOOL_DEBUG": "1"}):
        # Create a modified version
        modified = GlobalOverrides.from_active(
            debug=logging.WARNING, subprocess_timeout=200
        )

        # Export it
        modified.export(monkeypatch)

        # Verify it was exported correctly
        assert os.environ["TOOL_DEBUG"] == "30"  # WARNING
        assert os.environ["TOOL_SUBPROCESS_TIMEOUT"] == "200"


def test_nested_from_active_contexts() -> None:
    """Test nested contexts using from_active()."""
    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "DEBUG"}):
        from vcs_versioning.overrides import get_active_overrides

        # Original: DEBUG level
        assert get_active_overrides().debug == logging.DEBUG

        with GlobalOverrides.from_active(debug=logging.INFO):
            # Modified: INFO level
            assert get_active_overrides().debug == logging.INFO

            with GlobalOverrides.from_active(debug=logging.WARNING):
                # Further modified: WARNING level
                assert get_active_overrides().debug == logging.WARNING

            # Back to INFO
            assert get_active_overrides().debug == logging.INFO

        # Back to DEBUG
        assert get_active_overrides().debug == logging.DEBUG


def test_export_without_source_date_epoch() -> None:
    """Test that export() handles None source_date_epoch correctly."""
    overrides = GlobalOverrides.from_env("TEST", env={})

    target_env: dict[str, str] = {}
    overrides.export(target_env)

    # SOURCE_DATE_EPOCH should not be in the exported env
    assert "SOURCE_DATE_EPOCH" not in target_env
    assert "TEST_DEBUG" in target_env
    assert "TEST_SUBPROCESS_TIMEOUT" in target_env
    assert "TEST_HG_COMMAND" in target_env


def test_from_active_multiple_fields() -> None:
    """Test changing multiple fields at once with from_active()."""
    env = {
        "TEST_DEBUG": "DEBUG",
        "TEST_SUBPROCESS_TIMEOUT": "50",
        "TEST_HG_COMMAND": "hg",
        "SOURCE_DATE_EPOCH": "1000000000",
    }

    with GlobalOverrides.from_env("TEST", env=env):
        # Change multiple fields
        with GlobalOverrides.from_active(
            debug=logging.ERROR,
            subprocess_timeout=999,
            hg_command="/custom/hg",
            source_date_epoch=2000000000,
        ):
            from vcs_versioning.overrides import get_active_overrides

            active = get_active_overrides()
            assert active.debug == logging.ERROR
            assert active.subprocess_timeout == 999
            assert active.hg_command == "/custom/hg"
            assert active.source_date_epoch == 2000000000
            # Tool should be preserved
            assert active.tool == "TEST"


def test_export_roundtrip() -> None:
    """Test that export -> from_env produces equivalent overrides."""
    original = GlobalOverrides.from_env(
        "TEST",
        env={
            "TEST_DEBUG": "WARNING",
            "TEST_SUBPROCESS_TIMEOUT": "123",
            "TEST_HG_COMMAND": "/my/hg",
            "SOURCE_DATE_EPOCH": "1234567890",
        },
    )

    # Export to dict
    exported_env: dict[str, str] = {}
    original.export(exported_env)

    # Create new overrides from exported env
    recreated = GlobalOverrides.from_env("TEST", env=exported_env)

    # Should be equivalent
    assert recreated.debug == original.debug
    assert recreated.subprocess_timeout == original.subprocess_timeout
    assert recreated.hg_command == original.hg_command
    assert recreated.source_date_epoch == original.source_date_epoch
    assert recreated.tool == original.tool


def test_from_active_preserves_tool() -> None:
    """Test that from_active() preserves the tool prefix."""
    with GlobalOverrides.from_env("CUSTOM_TOOL", env={"CUSTOM_TOOL_DEBUG": "1"}):
        with GlobalOverrides.from_active(subprocess_timeout=999):
            from vcs_versioning.overrides import get_active_overrides

            active = get_active_overrides()
            assert active.tool == "CUSTOM_TOOL"


def test_export_with_different_debug_levels() -> None:
    """Test that export() correctly formats different debug levels."""
    test_cases = [
        (False, "0"),
        (logging.DEBUG, "10"),
        (logging.INFO, "20"),
        (logging.WARNING, "30"),
        (logging.ERROR, "40"),
        (logging.CRITICAL, "50"),
    ]

    for debug_val, expected_str in test_cases:
        # Need an active context to use from_active()
        with GlobalOverrides.from_env("TEST", env={}):
            modified = GlobalOverrides.from_active(debug=debug_val)

            target_env: dict[str, str] = {}
            modified.export(target_env)

            assert target_env["TEST_DEBUG"] == expected_str, (
                f"Expected {expected_str} for debug={debug_val}, got {target_env['TEST_DEBUG']}"
            )


def test_from_active_with_source_date_epoch_none() -> None:
    """Test that from_active() can clear source_date_epoch."""
    with GlobalOverrides.from_env("TEST", env={"SOURCE_DATE_EPOCH": "1234567890"}):
        from vcs_versioning.overrides import get_active_overrides

        # Original has epoch set
        assert get_active_overrides().source_date_epoch == 1234567890

        # Clear it with from_active
        with GlobalOverrides.from_active(source_date_epoch=None):
            assert get_active_overrides().source_date_epoch is None


def test_export_integration_with_subprocess_pattern() -> None:
    """Test the common pattern of exporting for subprocess calls."""

    # Simulate the pattern used in tests
    with GlobalOverrides.from_env("TOOL", env={"TOOL_DEBUG": "INFO"}):
        modified = GlobalOverrides.from_active(
            subprocess_timeout=5, debug=logging.DEBUG
        )

        # Export to a clean environment
        subprocess_env: dict[str, str] = {}
        modified.export(subprocess_env)

        # Verify subprocess would get the right values
        assert subprocess_env["TOOL_DEBUG"] == "10"  # DEBUG
        assert subprocess_env["TOOL_SUBPROCESS_TIMEOUT"] == "5"

        # Can be used with subprocess.run
        # subprocess.run(["cmd"], env=subprocess_env)


def test_env_reader_property() -> None:
    """Test that GlobalOverrides provides a configured EnvReader."""
    env = {
        "TOOL_CUSTOM_VAR": "value1",
        "VCS_VERSIONING_FALLBACK_VAR": "value2",
        "TOOL_VAR_FOR_MY_PKG": "dist_specific",
    }

    # Without dist_name
    with GlobalOverrides.from_env("TOOL", env=env) as overrides:
        reader = overrides.env_reader
        assert reader.read("CUSTOM_VAR") == "value1"
        assert reader.read("FALLBACK_VAR") == "value2"  # Uses VCS_VERSIONING fallback
        assert reader.read("NONEXISTENT") is None

    # With dist_name
    with GlobalOverrides.from_env("TOOL", env=env, dist_name="my-pkg") as overrides:
        reader = overrides.env_reader
        assert reader.read("VAR") == "dist_specific"  # Dist-specific takes precedence


def test_env_reader_property_with_dist_name() -> None:
    """Test EnvReader property with distribution-specific variables."""
    env = {
        "TOOL_CONFIG_FOR_MY_PACKAGE": '{local_scheme = "no-local"}',
        "TOOL_CONFIG": '{version_scheme = "guess-next-dev"}',
    }

    from typing import TypedDict

    class TestSchema(TypedDict, total=False):
        local_scheme: str
        version_scheme: str

    with GlobalOverrides.from_env("TOOL", env=env, dist_name="my-package") as overrides:
        # Should read dist-specific TOML
        config = overrides.env_reader.read_toml("CONFIG", schema=TestSchema)
        assert config == {"local_scheme": "no-local"}

    # Without dist_name, gets generic
    with GlobalOverrides.from_env("TOOL", env=env) as overrides:
        config = overrides.env_reader.read_toml("CONFIG", schema=TestSchema)
        assert config == {"version_scheme": "guess-next-dev"}


class TestEnvReader:
    """Tests for the EnvReader class."""

    def test_requires_tools_names(self) -> None:
        """Test that EnvReader requires tools_names to be provided."""
        from vcs_versioning.overrides import EnvReader

        with pytest.raises(TypeError, match="tools_names must be a non-empty tuple"):
            EnvReader(tools_names=(), env={})

    def test_empty_tools_names_raises(self) -> None:
        """Test that empty tools_names raises an error."""
        from vcs_versioning.overrides import EnvReader

        with pytest.raises(TypeError, match="tools_names must be a non-empty tuple"):
            EnvReader(tools_names=(), env={})

    def test_read_generic_first_tool(self) -> None:
        """Test reading generic env var from first tool."""
        from vcs_versioning.overrides import EnvReader

        env = {"TOOL_A_DEBUG": "1"}
        reader = EnvReader(tools_names=("TOOL_A", "TOOL_B"), env=env)
        assert reader.read("DEBUG") == "1"

    def test_read_generic_fallback_to_second_tool(self) -> None:
        """Test falling back to second tool when first not found."""
        from vcs_versioning.overrides import EnvReader

        env = {"TOOL_B_DEBUG": "2"}
        reader = EnvReader(tools_names=("TOOL_A", "TOOL_B"), env=env)
        assert reader.read("DEBUG") == "2"

    def test_read_generic_first_tool_wins(self) -> None:
        """Test that first tool takes precedence."""
        from vcs_versioning.overrides import EnvReader

        env = {"TOOL_A_DEBUG": "1", "TOOL_B_DEBUG": "2"}
        reader = EnvReader(tools_names=("TOOL_A", "TOOL_B"), env=env)
        assert reader.read("DEBUG") == "1"

    def test_read_not_found(self) -> None:
        """Test that None is returned when env var not found."""
        from vcs_versioning.overrides import EnvReader

        reader = EnvReader(tools_names=("TOOL_A", "TOOL_B"), env={})
        assert reader.read("DEBUG") is None

    def test_read_dist_specific_first_tool(self) -> None:
        """Test reading dist-specific env var from first tool."""
        from vcs_versioning.overrides import EnvReader

        env = {"TOOL_A_PRETEND_VERSION_FOR_MY_PACKAGE": "1.0.0"}
        reader = EnvReader(
            tools_names=("TOOL_A", "TOOL_B"), env=env, dist_name="my-package"
        )
        assert reader.read("PRETEND_VERSION") == "1.0.0"

    def test_read_dist_specific_fallback_to_second_tool(self) -> None:
        """Test falling back to second tool for dist-specific."""
        from vcs_versioning.overrides import EnvReader

        env = {"TOOL_B_PRETEND_VERSION_FOR_MY_PACKAGE": "2.0.0"}
        reader = EnvReader(
            tools_names=("TOOL_A", "TOOL_B"), env=env, dist_name="my-package"
        )
        assert reader.read("PRETEND_VERSION") == "2.0.0"

    def test_read_dist_specific_takes_precedence_over_generic(self) -> None:
        """Test that dist-specific takes precedence over generic."""
        from vcs_versioning.overrides import EnvReader

        env = {
            "TOOL_A_PRETEND_VERSION_FOR_MY_PACKAGE": "1.0.0",
            "TOOL_A_PRETEND_VERSION": "2.0.0",
        }
        reader = EnvReader(
            tools_names=("TOOL_A", "TOOL_B"), env=env, dist_name="my-package"
        )
        assert reader.read("PRETEND_VERSION") == "1.0.0"

    def test_read_dist_specific_second_tool_over_generic_first_tool(self) -> None:
        """Test that dist-specific from second tool beats generic from first tool."""
        from vcs_versioning.overrides import EnvReader

        env = {
            "TOOL_B_PRETEND_VERSION_FOR_MY_PACKAGE": "2.0.0",
            "TOOL_A_PRETEND_VERSION": "1.0.0",
        }
        reader = EnvReader(
            tools_names=("TOOL_A", "TOOL_B"), env=env, dist_name="my-package"
        )
        # Dist-specific from TOOL_B should win
        assert reader.read("PRETEND_VERSION") == "2.0.0"

    def test_read_falls_back_to_generic_when_no_dist_specific(self) -> None:
        """Test falling back to generic when dist-specific not found."""
        from vcs_versioning.overrides import EnvReader

        env = {"TOOL_B_PRETEND_VERSION": "2.0.0"}
        reader = EnvReader(
            tools_names=("TOOL_A", "TOOL_B"), env=env, dist_name="my-package"
        )
        assert reader.read("PRETEND_VERSION") == "2.0.0"

    def test_read_normalizes_dist_name(self) -> None:
        """Test that distribution names are normalized correctly."""
        from vcs_versioning.overrides import EnvReader

        env = {"TOOL_A_PRETEND_VERSION_FOR_MY_PACKAGE": "1.0.0"}
        # Try various equivalent dist names
        for dist_name in ["my-package", "My.Package", "my_package", "MY-PACKAGE"]:
            reader = EnvReader(tools_names=("TOOL_A",), env=env, dist_name=dist_name)
            assert reader.read("PRETEND_VERSION") == "1.0.0"

    def test_read_finds_alternative_normalization(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that read warns about alternative normalizations."""
        from vcs_versioning.overrides import EnvReader

        # Use a non-standard normalization
        env = {"TOOL_A_PRETEND_VERSION_FOR_MY-PACKAGE": "1.0.0"}
        reader = EnvReader(tools_names=("TOOL_A",), env=env, dist_name="my-package")

        with caplog.at_level(logging.WARNING):
            result = reader.read("PRETEND_VERSION")

        assert result == "1.0.0"
        assert "Found environment variable" in caplog.text
        assert "but expected" in caplog.text
        assert "TOOL_A_PRETEND_VERSION_FOR_MY_PACKAGE" in caplog.text

    def test_read_suggests_close_matches(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that read suggests close matches for typos."""
        from vcs_versioning.overrides import EnvReader

        # Use a typo in dist name
        env = {"TOOL_A_PRETEND_VERSION_FOR_MY_PACKGE": "1.0.0"}
        reader = EnvReader(tools_names=("TOOL_A",), env=env, dist_name="my-package")

        with caplog.at_level(logging.WARNING):
            result = reader.read("PRETEND_VERSION")

        assert result is None
        assert "Did you mean" in caplog.text

    def test_read_returns_exact_match_without_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that exact matches don't trigger diagnostics."""
        from vcs_versioning.overrides import EnvReader

        env = {"TOOL_A_PRETEND_VERSION_FOR_MY_PACKAGE": "1.0.0"}
        reader = EnvReader(tools_names=("TOOL_A",), env=env, dist_name="my-package")

        with caplog.at_level(logging.WARNING):
            result = reader.read("PRETEND_VERSION")

        assert result == "1.0.0"
        # No warnings should be logged for exact matches
        assert not caplog.records

    def test_read_toml_inline_map(self) -> None:
        """Test reading an inline TOML map."""
        from vcs_versioning._overrides import ConfigOverridesDict
        from vcs_versioning.overrides import EnvReader

        env = {
            "TOOL_A_OVERRIDES": '{local_scheme = "no-local-version", version_scheme = "release-branch-semver"}'
        }
        reader = EnvReader(tools_names=("TOOL_A",), env=env)

        result = reader.read_toml("OVERRIDES", schema=ConfigOverridesDict)
        assert result == {
            "local_scheme": "no-local-version",
            "version_scheme": "release-branch-semver",
        }

    def test_read_toml_full_document(self) -> None:
        """Test reading a full TOML document."""
        from vcs_versioning._overrides import PretendMetadataDict
        from vcs_versioning.overrides import EnvReader

        env = {
            "TOOL_A_PRETEND_METADATA": 'tag = "v1.0.0"\ndistance = 4\nnode = "g123abc"'
        }
        reader = EnvReader(tools_names=("TOOL_A",), env=env)

        result = reader.read_toml("PRETEND_METADATA", schema=PretendMetadataDict)
        assert result == {"tag": "v1.0.0", "distance": 4, "node": "g123abc"}

    def test_read_toml_not_found_returns_empty_dict(self) -> None:
        """Test that read_toml returns empty dict when not found."""
        from vcs_versioning._overrides import ConfigOverridesDict
        from vcs_versioning.overrides import EnvReader

        reader = EnvReader(tools_names=("TOOL_A",), env={})

        result = reader.read_toml("OVERRIDES", schema=ConfigOverridesDict)
        assert result == {}

    def test_read_toml_empty_string_returns_empty_dict(self) -> None:
        """Test that empty string returns empty dict."""
        from vcs_versioning._overrides import ConfigOverridesDict
        from vcs_versioning.overrides import EnvReader

        env = {"TOOL_A_OVERRIDES": ""}
        reader = EnvReader(tools_names=("TOOL_A",), env=env)

        result = reader.read_toml("OVERRIDES", schema=ConfigOverridesDict)
        assert result == {}

    def test_read_toml_with_tool_fallback(self) -> None:
        """Test that read_toml respects tool fallback order."""
        from typing import TypedDict

        from vcs_versioning.overrides import EnvReader

        class _TestSchema(TypedDict, total=False):
            """Schema for this test without validation."""

            debug: bool

        env = {"TOOL_B_OVERRIDES": "{debug = true}"}
        reader = EnvReader(tools_names=("TOOL_A", "TOOL_B"), env=env)

        result = reader.read_toml("OVERRIDES", schema=_TestSchema)
        assert result == {"debug": True}

    def test_read_toml_with_dist_specific(self) -> None:
        """Test reading dist-specific TOML data."""
        from vcs_versioning._overrides import ConfigOverridesDict
        from vcs_versioning.overrides import EnvReader

        env = {
            "TOOL_A_OVERRIDES_FOR_MY_PACKAGE": '{local_scheme = "no-local-version"}',
            "TOOL_A_OVERRIDES": '{version_scheme = "guess-next-dev"}',
        }
        reader = EnvReader(tools_names=("TOOL_A",), env=env, dist_name="my-package")

        # Should get dist-specific version
        result = reader.read_toml("OVERRIDES", schema=ConfigOverridesDict)
        assert result == {"local_scheme": "no-local-version"}

    def test_read_toml_dist_specific_fallback_to_generic(self) -> None:
        """Test falling back to generic when dist-specific not found."""
        from vcs_versioning._overrides import ConfigOverridesDict
        from vcs_versioning.overrides import EnvReader

        env = {"TOOL_A_OVERRIDES": '{version_scheme = "guess-next-dev"}'}
        reader = EnvReader(tools_names=("TOOL_A",), env=env, dist_name="my-package")

        result = reader.read_toml("OVERRIDES", schema=ConfigOverridesDict)
        assert result == {"version_scheme": "guess-next-dev"}

    def test_read_toml_invalid_raises(self) -> None:
        """Test that invalid TOML raises InvalidTomlError."""
        from vcs_versioning._overrides import ConfigOverridesDict
        from vcs_versioning._toml import InvalidTomlError
        from vcs_versioning.overrides import EnvReader

        env = {"TOOL_A_OVERRIDES": "this is not valid toml {{{"}
        reader = EnvReader(tools_names=("TOOL_A",), env=env)

        with pytest.raises(InvalidTomlError, match="Invalid TOML content"):
            reader.read_toml("OVERRIDES", schema=ConfigOverridesDict)

    def test_read_toml_with_alternative_normalization(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that read_toml works with diagnostic warnings."""
        from typing import TypedDict

        from vcs_versioning.overrides import EnvReader

        class _TestSchema(TypedDict, total=False):
            """Schema for this test without validation."""

            key: str

        # Use a non-standard normalization
        env = {"TOOL_A_OVERRIDES_FOR_MY-PACKAGE": '{key = "value"}'}
        reader = EnvReader(tools_names=("TOOL_A",), env=env, dist_name="my-package")

        with caplog.at_level(logging.WARNING):
            result = reader.read_toml("OVERRIDES", schema=_TestSchema)

        assert result == {"key": "value"}
        assert "Found environment variable" in caplog.text
        assert "but expected" in caplog.text

    def test_read_toml_complex_metadata(self) -> None:
        """Test reading complex ScmVersion metadata."""
        from vcs_versioning._overrides import PretendMetadataDict
        from vcs_versioning.overrides import EnvReader

        env = {
            "TOOL_A_PRETEND_METADATA": '{tag = "v2.0.0", distance = 10, node = "gabcdef123", dirty = true, branch = "main"}'
        }
        reader = EnvReader(tools_names=("TOOL_A",), env=env)

        result = reader.read_toml("PRETEND_METADATA", schema=PretendMetadataDict)
        assert result["tag"] == "v2.0.0"
        assert result["distance"] == 10
        assert result["node"] == "gabcdef123"
        assert result["dirty"] is True
        assert result["branch"] == "main"

    def test_read_toml_with_schema_validation(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that schema validation filters invalid fields."""
        from typing import TypedDict

        from vcs_versioning.overrides import EnvReader

        # Define a test schema
        class TestSchema(TypedDict, total=False):
            valid_field: str
            another_valid: str

        env = {
            "TOOL_A_DATA": '{valid_field = "ok", invalid_field = "bad", another_valid = "also ok"}'
        }
        reader = EnvReader(tools_names=("TOOL_A",), env=env)

        with caplog.at_level(logging.WARNING):
            result = reader.read_toml("DATA", schema=TestSchema)

        # Invalid field should be removed
        assert result == {"valid_field": "ok", "another_valid": "also ok"}
        assert "invalid_field" not in result

        # Should have logged a warning about invalid fields
        assert "Invalid fields in TOML data" in caplog.text
        assert "invalid_field" in caplog.text


def test_read_toml_overrides_with_schema(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that read_toml_overrides validates against CONFIG_OVERRIDES_SCHEMA."""
    import os
    from unittest.mock import patch

    from vcs_versioning._overrides import read_toml_overrides

    # Mock the environment with valid and invalid fields
    mock_env = {
        "SETUPTOOLS_SCM_OVERRIDES": '{version_scheme = "guess-next-dev", local_scheme = "no-local-version", invalid_field = "bad"}'
    }

    with (
        patch.dict(os.environ, mock_env, clear=True),
        caplog.at_level(logging.WARNING),
    ):
        result = read_toml_overrides(dist_name=None)

    # Valid fields should be present
    assert result["version_scheme"] == "guess-next-dev"
    assert result["local_scheme"] == "no-local-version"

    # Invalid field should be removed
    assert "invalid_field" not in result

    # Should have logged a warning
    assert "Invalid fields in TOML data" in caplog.text
    assert "invalid_field" in caplog.text
