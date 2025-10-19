from __future__ import annotations

import logging

from vcs_versioning import _log


def test_log_levels_when_set() -> None:
    from vcs_versioning.overrides import GlobalOverrides

    # Empty string or "1" should map to DEBUG (10)
    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": ""}):
        assert _log._default_log_level() == logging.DEBUG

    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "1"}):
        assert _log._default_log_level() == logging.DEBUG

    # Level names should be recognized
    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "INFO"}):
        assert _log._default_log_level() == logging.INFO

    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "info"}):
        assert _log._default_log_level() == logging.INFO

    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "WARNING"}):
        assert _log._default_log_level() == logging.WARNING

    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "ERROR"}):
        assert _log._default_log_level() == logging.ERROR

    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "CRITICAL"}):
        assert _log._default_log_level() == logging.CRITICAL

    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "DEBUG"}):
        assert _log._default_log_level() == logging.DEBUG

    # Unknown string should default to DEBUG
    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "yes"}):
        assert _log._default_log_level() == logging.DEBUG

    # Explicit log level (>=2) should be used as-is
    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "10"}):
        assert _log._default_log_level() == logging.DEBUG

    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "20"}):
        assert _log._default_log_level() == logging.INFO

    with GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "30"}):
        assert _log._default_log_level() == logging.WARNING
