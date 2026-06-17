"""Internal helpers for backward-compatible workdir shims."""

from __future__ import annotations

import contextlib
import warnings

from collections.abc import Iterator

from vcs_versioning import _config
from vcs_versioning._backends import _scm_workdir


@contextlib.contextmanager
def _bind_config(
    workdir: _scm_workdir.ScmWorkdir, config: _config.Configuration | None
) -> Iterator[None]:
    """Temporarily bind *config* to *workdir*, ensuring ``env`` is available.

    When *config* is ``None`` this is a no-op, so callers don't need a guard.
    Accessing ``config.env`` within the bound context will create a fallback
    ``VcsEnvironment`` with a deprecation warning if one was not explicitly set.

    Emits a DeprecationWarning directing callers toward the workdir-centric API
    (``VcsEnvironment.build_config() -> config.discover_workdir()``).
    """
    warnings.warn(
        "Passing config to workdir methods is deprecated. "
        "Use VcsEnvironment.build_config() and config.discover_workdir() "
        "to obtain a configured workdir directly.",
        DeprecationWarning,
        stacklevel=3,
    )
    if config is None:
        yield
        return

    old_config = workdir._config
    workdir._config = config
    try:
        yield
    finally:
        workdir._config = old_config
