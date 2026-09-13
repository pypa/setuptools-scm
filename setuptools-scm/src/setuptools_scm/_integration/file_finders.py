"""``setuptools.file_finders`` entry point with a setuptools-scm env context.

setuptools invokes file finders from ``walk_revctrl()`` during
``egg_info``/``sdist``, long after ``infer_version`` has returned and its
:func:`~vcs_versioning.overrides.ensure_context` scope has exited.  Pointing
the entry point straight at ``vcs_versioning._file_finders:find_files`` left
that call with no active ``GlobalOverrides``, so the ``SETUPTOOLS_SCM_``
prefix was not in ``tool_names`` and documented settings -- notably
``SETUPTOOLS_SCM_SUBPROCESS_TIMEOUT`` and ``SETUPTOOLS_SCM_HG_COMMAND`` --
were silently ignored there.

This shim enters the context the same way the other setuptools hooks do,
and is where the entry point's deprecation is announced: reaching this
module *is* the signal that setuptools invoked the global file finder,
so no sniffing of the project layout is needed to tell that apart from a
library calling ``vcs_versioning`` directly.
"""

from __future__ import annotations

import logging
import warnings

from typing import TYPE_CHECKING

from vcs_versioning._file_finders import _scm_search_failed
from vcs_versioning._file_finders import find_files as _find_files
from vcs_versioning.overrides import ensure_context

if TYPE_CHECKING:
    from vcs_versioning import _types as _t

_setuptools_scm_logger = logging.getLogger("setuptools_scm")

_DEPRECATION_MESSAGE = (
    "The setuptools.file_finders entry point is deprecated and will be "
    "removed in a future major release. Configure setuptools-scm via "
    "[tool.setuptools_scm] in pyproject.toml, setuptools-scm[simple] in "
    "build-system.requires, or use_scm_version in setup.py; file inclusion "
    "will then use the workdir API instead."
)


def _warn_unconfigured() -> None:
    """Warn unless setuptools-scm already ran workdir discovery for this build.

    ``scm_search_known_failed()`` is entered only by ``ScmEggInfoMixin``,
    which is registered only for projects that configure setuptools-scm --
    so the signal being set already means "configured".  A configured
    project that *has* a workdir never reaches the entry point at all.
    """
    if _scm_search_failed.get():
        return
    warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=3)


def find_files(path: _t.PathT = "") -> list[str]:
    """Find files tracked by the SCM, with setuptools-scm env settings applied."""
    with ensure_context("SETUPTOOLS_SCM", additional_loggers=_setuptools_scm_logger):
        _warn_unconfigured()
        return _find_files(path)


__all__ = ["find_files"]
