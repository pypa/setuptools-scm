from __future__ import annotations

import logging

from vcs_versioning.overrides import GlobalOverrides


def test_log_levels_when_set() -> None:
    # Empty string or "1" should map to DEBUG (10)
    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": ""}) as overrides:
        assert overrides.log_level() == logging.DEBUG

    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "1"}) as overrides:
        assert overrides.log_level() == logging.DEBUG

    # Level names should be recognized
    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "INFO"}) as overrides:
        assert overrides.log_level() == logging.INFO

    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "info"}) as overrides:
        assert overrides.log_level() == logging.INFO

    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "WARNING"}) as overrides:
        assert overrides.log_level() == logging.WARNING

    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "ERROR"}) as overrides:
        assert overrides.log_level() == logging.ERROR

    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "CRITICAL"}) as overrides:
        assert overrides.log_level() == logging.CRITICAL

    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "DEBUG"}) as overrides:
        assert overrides.log_level() == logging.DEBUG

    # Unknown string should default to DEBUG
    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "yes"}) as overrides:
        assert overrides.log_level() == logging.DEBUG

    # Explicit log level (>=2) should be used as-is
    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "10"}) as overrides:
        assert overrides.log_level() == logging.DEBUG

    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "20"}) as overrides:
        assert overrides.log_level() == logging.INFO

    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "30"}) as overrides:
        assert overrides.log_level() == logging.WARNING
