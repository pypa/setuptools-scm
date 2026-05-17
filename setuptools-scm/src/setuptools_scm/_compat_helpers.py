"""Internal helpers for backward-compatible workdir shims."""

from __future__ import annotations

import contextlib

from collections.abc import Iterator

from vcs_versioning import _config
from vcs_versioning._backends import _scm_workdir


@contextlib.contextmanager
def _bind_config(
    workdir: _scm_workdir.ScmWorkdir, config: _config.Configuration | None
) -> Iterator[None]:
    """Temporarily bind *config* to *workdir*, ensuring ``_env`` is set.

    When *config* is ``None`` this is a no-op, so callers don't need a guard.
    """
    if config is None:
        yield
        return

    from vcs_versioning._environment import VcsEnvironment

    old_config = workdir._config
    old_env = config._env

    workdir._config = config
    if config._env is None:
        config._env = VcsEnvironment.from_env("SETUPTOOLS_SCM")
    try:
        yield
    finally:
        workdir._config = old_config
        config._env = old_env
