"""
Environment variable overrides API for VCS versioning.

This module provides tools for managing environment variable overrides
in a structured way, with support for custom tool prefixes and fallback
to VCS_VERSIONING_* variables.

Example usage:
    >>> from vcs_versioning.overrides import GlobalOverrides
    >>>
    >>> # Apply overrides for the entire execution scope
    >>> with GlobalOverrides.from_env("HATCH_VCS"):
    >>>     version = get_version(...)

See the integrators documentation for more details.
"""

from __future__ import annotations

import contextvars
import logging
import os
from collections.abc import Mapping, MutableMapping
from contextlib import ContextDecorator
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, TypedDict, TypeVar, overload

from packaging.utils import canonicalize_name

from ._overrides import (
    _find_close_env_var_matches,
    _search_env_vars_with_prefix,
)
from ._toml import load_toml_or_inline_map

# TypeVar for generic TypedDict support
TSchema = TypeVar("TSchema", bound=TypedDict)  # type: ignore[valid-type]

if TYPE_CHECKING:
    from pytest import MonkeyPatch

    from . import _environment

log = logging.getLogger(__name__)


class EnvReader:
    """Helper class to read environment variables with tool prefix fallback.

    This class provides a structured way to read environment variables by trying
    multiple tool prefixes in order, with support for distribution-specific variants.

    Attributes:
        tools_names: Tuple of tool prefixes to try in order (e.g., ("HATCH_VCS", "VCS_VERSIONING"))
        env: Environment mapping to read from
        dist_name: Optional distribution name for dist-specific env vars

    Example:
        >>> reader = EnvReader(
        ...     tools_names=("HATCH_VCS", "VCS_VERSIONING"),
        ...     env=os.environ,
        ...     dist_name="my-package"
        ... )
        >>> debug_val = reader.read("DEBUG")  # tries HATCH_VCS_DEBUG, then VCS_VERSIONING_DEBUG
        >>> pretend = reader.read("PRETEND_VERSION")  # tries dist-specific first, then generic
    """

    tools_names: tuple[str, ...]
    env: Mapping[str, str]
    dist_name: str | None

    def __init__(
        self,
        tools_names: tuple[str, ...],
        env: Mapping[str, str],
        dist_name: str | None = None,
    ):
        """Initialize the EnvReader.

        Args:
            tools_names: Tuple of tool prefixes to try in order (e.g., ("HATCH_VCS", "VCS_VERSIONING"))
            env: Environment mapping to read from
            dist_name: Optional distribution name for dist-specific variables
        """
        if not tools_names:
            raise TypeError("tools_names must be a non-empty tuple")
        self.tools_names = tools_names
        self.env = env
        self.dist_name = dist_name

    @overload
    def read(self, name: str, *, split: str) -> list[str]: ...

    @overload
    def read(self, name: str, *, split: str, default: list[str]) -> list[str]: ...

    @overload
    def read(self, name: str, *, default: str) -> str: ...

    @overload
    def read(self, name: str) -> str | None: ...

    def read(
        self, name: str, *, split: str | None = None, default: Any = None
    ) -> str | list[str] | None:
        """Read a named environment variable, trying each tool in tools_names order.

        If dist_name is provided, tries distribution-specific variants first
        (e.g., TOOL_NAME_FOR_DIST), then falls back to generic variants (e.g., TOOL_NAME).

        Also provides helpful diagnostics when similar environment variables are found
        but don't match exactly (e.g., typos or incorrect normalizations in distribution names).

        Args:
            name: The environment variable name component (e.g., "DEBUG", "PRETEND_VERSION")
            split: Optional separator to split the value by (e.g., os.pathsep for path lists)
            default: Default value to return if not found (defaults to None)

        Returns:
            - If split is provided and value found: list[str] of split values
            - If split is provided and not found: default value
            - If split is None and value found: str value
            - If split is None and not found: default value
        """
        # If dist_name is provided, try dist-specific variants first
        found_value: str | None = None
        if self.dist_name is not None:
            canonical_dist_name = canonicalize_name(self.dist_name)
            env_var_dist_name = canonical_dist_name.replace("-", "_").upper()

            # Try each tool's dist-specific variant
            for tool in self.tools_names:
                expected_env_var = f"{tool}_{name}_FOR_{env_var_dist_name}"
                val = self.env.get(expected_env_var)
                if val is not None:
                    found_value = val
                    break

        # Try generic versions for each tool
        if found_value is None:
            for tool in self.tools_names:
                val = self.env.get(f"{tool}_{name}")
                if val is not None:
                    found_value = val
                    break

        # Not found - if dist_name is provided, check for common mistakes
        if found_value is None and self.dist_name is not None:
            canonical_dist_name = canonicalize_name(self.dist_name)
            env_var_dist_name = canonical_dist_name.replace("-", "_").upper()

            # Try each tool prefix for fuzzy matching
            for tool in self.tools_names:
                expected_env_var = f"{tool}_{name}_FOR_{env_var_dist_name}"
                prefix = f"{tool}_{name}_FOR_"

                # Search for alternative normalizations
                matches = _search_env_vars_with_prefix(prefix, self.dist_name, self.env)
                if matches:
                    env_var_name, value = matches[0]
                    log.warning(
                        "Found environment variable '%s' for dist name '%s', "
                        "but expected '%s'. Consider using the standard normalized name.",
                        env_var_name,
                        self.dist_name,
                        expected_env_var,
                    )
                    if len(matches) > 1:
                        other_vars = [var for var, _ in matches[1:]]
                        log.warning(
                            "Multiple alternative environment variables found: %s. Using '%s'.",
                            other_vars,
                            env_var_name,
                        )
                    found_value = value
                    break

                # Search for close matches (potential typos)
                close_matches = _find_close_env_var_matches(
                    prefix, env_var_dist_name, self.env
                )
                if close_matches:
                    log.warning(
                        "Environment variable '%s' not found for dist name '%s' "
                        "(canonicalized as '%s'). Did you mean one of these? %s",
                        expected_env_var,
                        self.dist_name,
                        canonical_dist_name,
                        close_matches,
                    )

        # Process the found value or return default
        if found_value is not None:
            if split is not None:
                # Split the value by the provided separator, filtering out empty strings
                return [part for part in found_value.split(split) if part]
            return found_value
        # Return default, honoring the type based on split parameter
        if split is not None:
            # When split is provided, default should be a list
            return default if default is not None else []
        # For non-split case, default can be None or str
        return default  # type: ignore[no-any-return]

    def read_toml(self, name: str, *, schema: type[TSchema]) -> TSchema:
        """Read and parse a TOML-formatted environment variable.

        This method is useful for reading structured configuration like:
        - Config overrides (e.g., TOOL_OVERRIDES_FOR_DIST)
        - ScmVersion metadata (e.g., TOOL_PRETEND_METADATA_FOR_DIST)

        Supports both full TOML documents and inline TOML maps (starting with '{').

        Args:
            name: The environment variable name component (e.g., "OVERRIDES", "PRETEND_METADATA")
            schema: TypedDict class for schema validation.
                   Invalid fields will be logged as warnings and removed.

        Returns:
            Parsed TOML data conforming to the schema type, or an empty dict if not found.
            Raises InvalidTomlError if the TOML content is malformed.

        Example:
            >>> from typing import TypedDict
            >>> class MySchema(TypedDict, total=False):
            ...     local_scheme: str
            >>> reader = EnvReader(tools_names=("TOOL",), env={
            ...     "TOOL_OVERRIDES": '{local_scheme = "no-local-version"}',
            ... })
            >>> result: MySchema = reader.read_toml("OVERRIDES", schema=MySchema)
            >>> result["local_scheme"]
            'no-local-version'
        """
        data = self.read(name)
        return load_toml_or_inline_map(data, schema=schema)


class GlobalOverrides:
    """Global environment variable overrides for VCS versioning.

    Thin wrapper around :class:`~vcs_versioning._environment.VcsEnvironment`
    that adds context-manager semantics (logging configuration on entry)
    and backward-compatible attribute access.

    Use as a context manager to apply overrides for the execution scope.
    Logging is automatically configured when entering the context.

    Attributes:
        vcs_env: The underlying VcsEnvironment holding all parsed settings
        tool: Tool prefix used to read these overrides
        dist_name: Optional distribution name for dist-specific env var lookups
        additional_loggers: Logger instances to configure alongside vcs_versioning

    Usage:
        with GlobalOverrides.from_env("HATCH_VCS", dist_name="my-package") as overrides:
            # All modules now have access to these overrides
            # Logging is automatically configured based on HATCH_VCS_DEBUG

            # Read custom environment variables
            custom_val = overrides.env_reader.read("MY_CUSTOM_VAR")

            version = get_version(...)
    """

    __slots__ = ("vcs_env", "tool", "dist_name", "_token")

    def __init__(
        self,
        vcs_env: _environment.VcsEnvironment,
        tool: str,
        dist_name: str | None = None,
    ) -> None:
        self.vcs_env = vcs_env
        self.tool = tool
        self.dist_name = dist_name
        self._token: contextvars.Token[GlobalOverrides | None] | None = None

    # ------------------------------------------------------------------
    # Backward-compatible properties delegating to vcs_env
    # ------------------------------------------------------------------

    @property
    def debug(self) -> int | Literal[False]:
        return self.vcs_env.debug

    @property
    def subprocess_timeout(self) -> int:
        return self.vcs_env.subprocess_timeout

    @property
    def hg_command(self) -> str:
        return self.vcs_env.hg_command

    @property
    def source_date_epoch(self) -> int | None:
        return self.vcs_env.source_date_epoch

    @property
    def ignore_vcs_roots(self) -> list[str]:
        return list(self.vcs_env.ignore_vcs_roots)

    @property
    def additional_loggers(self) -> tuple[logging.Logger, ...]:
        return self.vcs_env.additional_loggers

    @property
    def env_reader(self) -> EnvReader:
        return self.vcs_env.make_reader(dist_name=self.dist_name)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def from_env(
        cls,
        tool: str,
        env: Mapping[str, str] = os.environ,
        dist_name: str | None = None,
        additional_loggers: logging.Logger | list[logging.Logger] | tuple[()] = (),
    ) -> GlobalOverrides:
        """Read all global overrides from environment variables.

        Delegates entirely to :meth:`VcsEnvironment.from_env` for env-var
        parsing, then wraps the result with context-manager semantics.

        Args:
            tool: Tool prefix (e.g., "HATCH_VCS", "SETUPTOOLS_SCM")
            env: Environment dict to read from (defaults to os.environ)
            dist_name: Optional distribution name for dist-specific env var lookups
            additional_loggers: Logger instance(s) to configure alongside vcs_versioning.
                Can be a single logger, a list of loggers, or empty tuple.

        Returns:
            GlobalOverrides instance ready to use as context manager
        """
        import dataclasses as dc

        from ._environment import VcsEnvironment

        vcs_env = VcsEnvironment.from_env(tool, env=env)

        logger_tuple: tuple[logging.Logger, ...]
        if isinstance(additional_loggers, logging.Logger):
            logger_tuple = (additional_loggers,)
        elif isinstance(additional_loggers, list):
            logger_tuple = tuple(additional_loggers)
        else:
            logger_tuple = ()

        if logger_tuple:
            vcs_env = dc.replace(vcs_env, additional_loggers=logger_tuple)

        return cls(
            vcs_env=vcs_env,
            tool=tool,
            dist_name=dist_name,
        )

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> GlobalOverrides:
        """Enter context: set this as the active override and configure logging."""
        self._token = _active_overrides.set(self)
        self.vcs_env.configure_logging()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        """Exit context: restore previous override state."""
        if self._token is not None:
            _active_overrides.reset(self._token)
            self._token = None

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def log_level(self) -> int:
        """Get the appropriate logging level from the debug setting."""
        return self.vcs_env.log_level()

    def source_epoch_or_utc_now(self) -> datetime:
        """Get datetime from SOURCE_DATE_EPOCH or current UTC time."""
        return self.vcs_env.source_epoch_or_utc_now()

    @classmethod
    def from_active(cls, **changes: Any) -> GlobalOverrides:
        """Create a new GlobalOverrides based on the currently active one.

        Supports changing ``dist_name``, ``tool``, ``additional_loggers``,
        and any ``VcsEnvironment`` field (``debug``, ``subprocess_timeout``,
        ``hg_command``, ``source_date_epoch``, ``ignore_vcs_roots``).

        If ``tool`` changes, a new ``VcsEnvironment`` is created by re-reading
        from the stored env mapping with the new tool prefix.

        Raises:
            RuntimeError: If no GlobalOverrides context is currently active
        """
        import dataclasses as dc

        from ._environment import VcsEnvironment

        active = _active_overrides.get()
        if active is None:
            raise RuntimeError(
                "Cannot call from_active() without an active GlobalOverrides context. "
                "Use from_env() to create the initial context."
            )

        new_tool = changes.pop("tool", active.tool)
        new_dist_name = changes.pop("dist_name", active.dist_name)

        if new_tool != active.tool:
            vcs_env = VcsEnvironment.from_env(new_tool, env=active.vcs_env._env)
        else:
            vcs_env = active.vcs_env

        # Remaining changes are VcsEnvironment field overrides (includes additional_loggers)
        vcs_env_fields = {f.name for f in dc.fields(VcsEnvironment)}
        env_changes = {k: v for k, v in changes.items() if k in vcs_env_fields}
        if env_changes:
            vcs_env = dc.replace(vcs_env, **env_changes)

        return cls(
            vcs_env=vcs_env,
            tool=new_tool,
            dist_name=new_dist_name,
        )

    def export(self, target: MutableMapping[str, str] | MonkeyPatch) -> None:
        """Export overrides to environment variables.

        Can export to either a dict-like environment or a pytest monkeypatch fixture.
        This is useful for tests that need to propagate overrides to subprocesses.
        """
        self.vcs_env.export(target)


# Thread-local storage for active global overrides
_active_overrides: contextvars.ContextVar[GlobalOverrides | None] = (
    contextvars.ContextVar("vcs_versioning_overrides", default=None)
)


class ensure_context(ContextDecorator):
    """Context manager/decorator that ensures a GlobalOverrides context is active.

    If no context is active, creates one using from_env() with the specified tool.
    Can be used as a decorator or context manager.

    Example as decorator:
        @ensure_context("SETUPTOOLS_SCM", additional_loggers=logging.getLogger("setuptools_scm"))
        def my_entry_point():
            # Will automatically have context
            pass

    Example as context manager:
        with ensure_context("SETUPTOOLS_SCM", additional_loggers=logging.getLogger("setuptools_scm")):
            # Will have context here
            pass
    """

    def __init__(
        self,
        tool: str,
        *,
        env: Mapping[str, str] | None = None,
        dist_name: str | None = None,
        additional_loggers: logging.Logger | list[logging.Logger] | tuple[()] = (),
    ):
        """Initialize the context ensurer.

        Args:
            tool: Tool name (e.g., "SETUPTOOLS_SCM", "vcs-versioning")
            env: Environment variables to read from (defaults to os.environ)
            dist_name: Optional distribution name
            additional_loggers: Logger instance(s) to configure
        """
        self.tool = tool
        self.env = env if env is not None else os.environ
        self.dist_name = dist_name
        self.additional_loggers = additional_loggers
        self._context: GlobalOverrides | None = None
        self._created_context = False

    def __enter__(self) -> GlobalOverrides:
        """Enter context: create GlobalOverrides if none is active."""
        # Check if there's already an active context
        existing: GlobalOverrides | None = _active_overrides.get()

        if existing is not None:
            # Already have a context, just return it
            self._created_context = False
            return existing

        # No context active, create one
        self._created_context = True
        self._context = GlobalOverrides.from_env(
            self.tool,
            env=self.env,
            dist_name=self.dist_name,
            additional_loggers=self.additional_loggers,
        )
        return self._context.__enter__()

    def __exit__(self, *exc_info: Any) -> None:
        """Exit context: only exit if we created the context."""
        if self._created_context and self._context is not None:
            self._context.__exit__(*exc_info)


__all__ = [
    "EnvReader",
    "GlobalOverrides",
    "ensure_context",
]
