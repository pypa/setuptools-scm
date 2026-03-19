"""
logging helpers, supports vendoring
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Iterator


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


def _get_all_scm_loggers(
    additional_loggers: list[logging.Logger] | None = None,
) -> list[logging.Logger]:
    """Get all SCM-related loggers that need configuration.

    Always configures vcs_versioning logger.
    If additional_loggers is provided, also configures those loggers.
    If not provided, tries to get them from active GlobalOverrides context.
    """
    loggers = [logging.getLogger("vcs_versioning")]

    if additional_loggers is not None:
        loggers.extend(additional_loggers)
    else:
        # Try to get additional loggers from active overrides context
        try:
            from .overrides import _active_overrides

            overrides = _active_overrides.get()
            if overrides is not None:
                loggers.extend(overrides.additional_loggers)
        except ImportError:
            # During early initialization, overrides module might not be available yet
            pass

    return loggers


_default_handler: logging.Handler | None = None


def _configure_loggers(
    log_level: int, additional_loggers: list[logging.Logger] | None = None
) -> None:
    """Internal function to configure SCM-related loggers.

    This is called automatically by GlobalOverrides.__enter__().
    Do not call directly - use GlobalOverrides context manager instead.

    Args:
        log_level: Logging level constant from logging module
        additional_loggers: Optional list of additional logger instances to configure
    """
    global _default_handler

    if _default_handler is None:
        _default_handler = make_default_handler()

    for logger in _get_all_scm_loggers(additional_loggers):
        if not logger.handlers:
            logger.addHandler(_default_handler)
        logger.setLevel(log_level)
        logger.propagate = False


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
