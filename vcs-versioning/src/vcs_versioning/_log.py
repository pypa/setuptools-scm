"""
logging helpers, supports vendoring
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Iterator

# Logger names that need configuration
LOGGER_NAMES = [
    "vcs_versioning",
    "setuptools_scm",
]


def make_default_handler() -> logging.Handler:
    try:
        from rich.console import Console

        console = Console(stderr=True)
        from rich.logging import RichHandler

        return RichHandler(console=console)
    except ImportError:
        last_resort = logging.lastResort
        assert last_resort is not None
        return last_resort


def _get_all_scm_loggers() -> list[logging.Logger]:
    """Get all SCM-related loggers that need configuration."""
    return [logging.getLogger(name) for name in LOGGER_NAMES]


_configured = False
_default_handler: logging.Handler | None = None


def configure_logging(log_level: int = logging.WARNING) -> None:
    """Configure logging for all SCM-related loggers.

    This should be called once at entry point (CLI, setuptools integration, etc.)
    before any actual logging occurs.

    Args:
        log_level: Logging level constant from logging module (DEBUG, INFO, WARNING, etc.)
                   Defaults to WARNING.
    """
    global _configured, _default_handler
    if _configured:
        return

    if _default_handler is None:
        _default_handler = make_default_handler()

    for logger in _get_all_scm_loggers():
        if not logger.handlers:
            logger.addHandler(_default_handler)
        logger.setLevel(log_level)
        logger.propagate = False

    _configured = True


# The vcs_versioning root logger
# Note: This is created on import, but configured lazily via configure_logging()
log = logging.getLogger("vcs_versioning")


@contextlib.contextmanager
def defer_to_pytest() -> Iterator[None]:
    """Configure all SCM loggers to propagate to pytest's log capture."""
    loggers = _get_all_scm_loggers()
    old_states = []

    for logger in loggers:
        old_states.append((logger, logger.propagate, logger.level, logger.handlers[:]))
        logger.propagate = True
        logger.setLevel(logging.NOTSET)
        # Remove all handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    try:
        yield
    finally:
        for logger, old_propagate, old_level, old_handlers in old_states:
            for handler in old_handlers:
                logger.addHandler(handler)
            logger.propagate = old_propagate
            logger.setLevel(old_level)


@contextlib.contextmanager
def enable_debug(handler: logging.Handler | None = None) -> Iterator[None]:
    """Enable debug logging for all SCM loggers."""
    global _default_handler
    if handler is None:
        if _default_handler is None:
            _default_handler = make_default_handler()
        handler = _default_handler

    loggers = _get_all_scm_loggers()
    old_states = []

    for logger in loggers:
        old_states.append((logger, logger.level))
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

    old_handler_level = handler.level
    handler.setLevel(logging.DEBUG)

    try:
        yield
    finally:
        handler.setLevel(old_handler_level)
        for logger, old_level in old_states:
            logger.setLevel(old_level)
            if handler is not _default_handler:
                logger.removeHandler(handler)
