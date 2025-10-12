"""
Logging configuration for setuptools_scm
"""

from __future__ import annotations

import logging

# Import shared logging configuration from vcs_versioning
# This will configure both vcs_versioning and setuptools_scm loggers
from vcs_versioning._log import configure_logging
from vcs_versioning._log import defer_to_pytest
from vcs_versioning._log import enable_debug

# Create our own root logger
log = logging.getLogger(__name__.rsplit(".", 1)[0])
log.propagate = False

# Ensure both loggers are configured
configure_logging()

__all__ = ["configure_logging", "defer_to_pytest", "enable_debug", "log"]
