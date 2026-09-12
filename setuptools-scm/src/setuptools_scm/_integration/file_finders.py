"""``setuptools.file_finders`` entry point with a setuptools-scm env context.

setuptools invokes file finders from ``walk_revctrl()`` during
``egg_info``/``sdist``, long after ``infer_version`` has returned and its
:func:`~vcs_versioning.overrides.ensure_context` scope has exited.  Pointing
the entry point straight at ``vcs_versioning._file_finders:find_files`` left
that call with no active ``GlobalOverrides``, so the ``SETUPTOOLS_SCM_``
prefix was not in ``tool_names`` and documented settings -- notably
``SETUPTOOLS_SCM_SUBPROCESS_TIMEOUT`` and ``SETUPTOOLS_SCM_HG_COMMAND`` --
were silently ignored there.

This shim enters the context the same way the other setuptools hooks do.
"""

from __future__ import annotations

import logging

from typing import TYPE_CHECKING

from vcs_versioning._file_finders import find_files as _find_files
from vcs_versioning.overrides import ensure_context

if TYPE_CHECKING:
    from vcs_versioning import _types as _t

_setuptools_scm_logger = logging.getLogger("setuptools_scm")


def find_files(path: _t.PathT = "") -> list[str]:
    """Find files tracked by the SCM, with setuptools-scm env settings applied."""
    with ensure_context("SETUPTOOLS_SCM", additional_loggers=_setuptools_scm_logger):
        return _find_files(path)


__all__ = ["find_files"]
