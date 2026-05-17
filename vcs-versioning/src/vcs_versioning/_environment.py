"""Explicit runtime environment for the workdir-based API.

``VcsEnvironment`` captures runtime settings (subprocess timeout, hg command,
SOURCE_DATE_EPOCH, etc.) from the process environment at creation time and
uses them to build ``Configuration`` objects.  This is the entry point of the
chain::

    env -> config -> workdir -> scm_version -> formatted version string

No ``ContextVar`` or context manager is needed.
"""

from __future__ import annotations

import dataclasses
import logging
import os
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ._config import Configuration

log = logging.getLogger(__name__)

_DEFAULT_SUBPROCESS_TIMEOUT = 40
_DEFAULT_HG_COMMAND = "hg"


@dataclasses.dataclass(frozen=True)
class VcsEnvironment:
    """Runtime environment captured from env vars at creation time.

    Use :meth:`from_env` to read settings from the process environment,
    then :meth:`build_config` to create a ``Configuration`` that carries
    these settings through the rest of the pipeline.
    """

    subprocess_timeout: int = _DEFAULT_SUBPROCESS_TIMEOUT
    hg_command: str = _DEFAULT_HG_COMMAND
    source_date_epoch: int | None = None
    ignore_vcs_roots: tuple[str, ...] = ()
    tool_names: tuple[str, ...] = ("VCS_VERSIONING",)

    @classmethod
    def from_env(
        cls,
        *tool_names: str,
        env: Mapping[str, str] | None = None,
    ) -> VcsEnvironment:
        """Read runtime settings from environment variables.

        Positional *tool_names* are tried in order as env-var prefixes,
        with ``VCS_VERSIONING`` always appended as the final fallback.
        """
        if env is None:
            env = os.environ

        all_names = (*tool_names, "VCS_VERSIONING")

        from .overrides import EnvReader

        reader = EnvReader(tools_names=all_names, env=env, dist_name=None)

        timeout_val = reader.read("SUBPROCESS_TIMEOUT")
        subprocess_timeout = _DEFAULT_SUBPROCESS_TIMEOUT
        if timeout_val is not None:
            try:
                subprocess_timeout = int(timeout_val)
            except ValueError:
                log.warning(
                    "Invalid SUBPROCESS_TIMEOUT value '%s', using default %d",
                    timeout_val,
                    subprocess_timeout,
                )

        hg_command = reader.read("HG_COMMAND") or _DEFAULT_HG_COMMAND

        source_date_epoch_val = env.get("SOURCE_DATE_EPOCH")
        source_date_epoch: int | None = None
        if source_date_epoch_val is not None:
            try:
                source_date_epoch = int(source_date_epoch_val)
            except ValueError:
                log.warning(
                    "Invalid SOURCE_DATE_EPOCH value '%s', ignoring",
                    source_date_epoch_val,
                )

        ignore_vcs_roots_raw = reader.read(
            "IGNORE_VCS_ROOTS", split=os.pathsep, default=[]
        )
        ignore_vcs_roots = tuple(os.path.normcase(p) for p in ignore_vcs_roots_raw)

        return cls(
            subprocess_timeout=subprocess_timeout,
            hg_command=hg_command,
            source_date_epoch=source_date_epoch,
            ignore_vcs_roots=ignore_vcs_roots,
            tool_names=all_names,
        )

    def build_config(self, **kwargs: Any) -> Configuration:
        """Create a ``Configuration`` that carries this environment.

        All *kwargs* are forwarded to ``Configuration.from_file``.
        The resulting config has ``_env`` set to this ``VcsEnvironment``
        so that downstream code (git/hg backends, ScmVersion construction)
        can read runtime settings without a ContextVar.
        """
        from ._config import Configuration

        config = Configuration.from_file(**kwargs)
        object.__setattr__(config, "_env", self)
        return config
