"""Explicit runtime environment for the workdir-based API.

``VcsEnvironment`` captures runtime settings (subprocess timeout, hg command,
SOURCE_DATE_EPOCH, debug level, etc.) from the process environment at creation
time and uses them to build ``Configuration`` objects.  This is the entry point
of the chain::

    env -> config -> workdir -> scm_version -> formatted version string

No ``ContextVar`` or context manager is needed.
"""

from __future__ import annotations

import dataclasses
import logging
import os
from collections.abc import Mapping, MutableMapping
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from pytest import MonkeyPatch

    from . import _config, overrides

log = logging.getLogger(__name__)

_DEFAULT_SUBPROCESS_TIMEOUT = 40
_DEFAULT_HG_COMMAND = "hg"


def _parse_debug(value: str | None) -> int | Literal[False]:
    """Parse a DEBUG env-var value into a log level or False."""
    if value is None:
        return False
    try:
        parsed_int = int(value)
        if parsed_int in (0, 1):
            return logging.DEBUG if parsed_int else False
        return parsed_int
    except ValueError:
        level_value = getattr(logging, value.upper(), None)
        if isinstance(level_value, int):
            return level_value
        return logging.DEBUG


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
    debug: int | Literal[False] = False
    _env: Mapping[str, str] = dataclasses.field(
        default_factory=lambda: os.environ, repr=False, compare=False
    )
    additional_loggers: tuple[logging.Logger, ...] = ()

    def log_level(self) -> int:
        """Logging level derived from the debug setting."""
        if self.debug is False:
            return logging.WARNING
        return self.debug

    def configure_logging(self) -> None:
        """Configure all loggers for this environment's debug level."""
        from ._log import _configure_loggers

        _configure_loggers(
            log_level=self.log_level(),
            additional_loggers=list(self.additional_loggers),
        )

    def make_reader(self, dist_name: str | None = None) -> overrides.EnvReader:
        """Create an :class:`EnvReader` configured with this env's tool names."""
        from .overrides import EnvReader

        return EnvReader(
            tools_names=self.tool_names, env=self._env, dist_name=dist_name
        )

    def source_epoch_or_utc_now(self) -> datetime:
        """Get datetime from SOURCE_DATE_EPOCH or current UTC time."""
        from datetime import timezone

        if self.source_date_epoch is not None:
            return datetime.fromtimestamp(self.source_date_epoch, timezone.utc)
        return datetime.now(timezone.utc)

    def export(self, target: MutableMapping[str, str] | MonkeyPatch) -> None:
        """Export settings to environment variables using ``tool_names[0]`` as prefix."""

        def set_var(key: str, value: str) -> None:
            if isinstance(target, MutableMapping):
                target[key] = value
            else:
                target.setenv(key, value)

        if self.source_date_epoch is not None:
            set_var("SOURCE_DATE_EPOCH", str(self.source_date_epoch))

        prefix = self.tool_names[0]

        if self.debug is False:
            set_var(f"{prefix}_DEBUG", "0")
        else:
            set_var(f"{prefix}_DEBUG", str(self.debug))

        set_var(f"{prefix}_SUBPROCESS_TIMEOUT", str(self.subprocess_timeout))
        set_var(f"{prefix}_HG_COMMAND", self.hg_command)

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

        debug = _parse_debug(reader.read("DEBUG"))

        return cls(
            subprocess_timeout=subprocess_timeout,
            hg_command=hg_command,
            source_date_epoch=source_date_epoch,
            ignore_vcs_roots=ignore_vcs_roots,
            tool_names=all_names,
            debug=debug,
            _env=env,
        )

    def build_config(self, **kwargs: Any) -> _config.Configuration:
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
