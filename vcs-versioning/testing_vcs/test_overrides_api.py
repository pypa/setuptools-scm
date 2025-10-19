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
        from vcs_versioning import _log

        # Original: DEBUG level
        assert _log._default_log_level() == logging.DEBUG

        with GlobalOverrides.from_active(debug=logging.INFO):
            # Modified: INFO level
            assert _log._default_log_level() == logging.INFO

            with GlobalOverrides.from_active(debug=logging.WARNING):
                # Further modified: WARNING level
                assert _log._default_log_level() == logging.WARNING

            # Back to INFO
            assert _log._default_log_level() == logging.INFO

        # Back to DEBUG
        assert _log._default_log_level() == logging.DEBUG


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
