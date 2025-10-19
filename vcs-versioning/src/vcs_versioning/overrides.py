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

import logging
import os
import warnings
from collections.abc import Mapping, MutableMapping
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from packaging.utils import canonicalize_name

from ._overrides import (
    _find_close_env_var_matches,
    _search_env_vars_with_prefix,
)
from ._toml import load_toml_or_inline_map

if TYPE_CHECKING:
    from pytest import MonkeyPatch

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

    def read(self, name: str) -> str | None:
        """Read a named environment variable, trying each tool in tools_names order.

        If dist_name is provided, tries distribution-specific variants first
        (e.g., TOOL_NAME_FOR_DIST), then falls back to generic variants (e.g., TOOL_NAME).

        Also provides helpful diagnostics when similar environment variables are found
        but don't match exactly (e.g., typos or incorrect normalizations in distribution names).

        Args:
            name: The environment variable name component (e.g., "DEBUG", "PRETEND_VERSION")

        Returns:
            The first matching environment variable value, or None if not found
        """
        # If dist_name is provided, try dist-specific variants first
        if self.dist_name is not None:
            canonical_dist_name = canonicalize_name(self.dist_name)
            env_var_dist_name = canonical_dist_name.replace("-", "_").upper()

            # Try each tool's dist-specific variant
            for tool in self.tools_names:
                expected_env_var = f"{tool}_{name}_FOR_{env_var_dist_name}"
                val = self.env.get(expected_env_var)
                if val is not None:
                    return val

        # Try generic versions for each tool
        for tool in self.tools_names:
            val = self.env.get(f"{tool}_{name}")
            if val is not None:
                return val

        # Not found - if dist_name is provided, check for common mistakes
        if self.dist_name is not None:
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
                    return value

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

        return None

    def read_toml(self, name: str) -> dict[str, Any]:
        """Read and parse a TOML-formatted environment variable.

        This method is useful for reading structured configuration like:
        - Config overrides (e.g., TOOL_OVERRIDES_FOR_DIST)
        - ScmVersion metadata (e.g., TOOL_PRETEND_METADATA_FOR_DIST)

        Supports both full TOML documents and inline TOML maps (starting with '{').

        Args:
            name: The environment variable name component (e.g., "OVERRIDES", "PRETEND_METADATA")

        Returns:
            Parsed TOML data as a dictionary, or an empty dict if not found or empty.
            Raises InvalidTomlError if the TOML content is malformed.

        Example:
            >>> reader = EnvReader(tools_names=("TOOL",), env={
            ...     "TOOL_OVERRIDES": '{"local_scheme": "no-local-version"}',
            ... })
            >>> reader.read_toml("OVERRIDES")
            {'local_scheme': 'no-local-version'}
        """
        data = self.read(name)
        return load_toml_or_inline_map(data)


@dataclass(frozen=True)
class GlobalOverrides:
    """Global environment variable overrides for VCS versioning.

    Use as a context manager to apply overrides for the execution scope.

    Attributes:
        debug: Debug logging level (int from logging module) or False to disable
        subprocess_timeout: Timeout for subprocess commands in seconds
        hg_command: Command to use for Mercurial operations
        source_date_epoch: Unix timestamp for reproducible builds (None if not set)
        tool: Tool prefix used to read these overrides

    Usage:
        with GlobalOverrides.from_env("HATCH_VCS"):
            # All modules now have access to these overrides
            version = get_version(...)
    """

    debug: int | Literal[False]
    subprocess_timeout: int
    hg_command: str
    source_date_epoch: int | None
    tool: str

    @classmethod
    def from_env(
        cls,
        tool: str,
        env: Mapping[str, str] = os.environ,
    ) -> GlobalOverrides:
        """Read all global overrides from environment variables.

        Checks both tool-specific prefix and VCS_VERSIONING prefix as fallback.

        Args:
            tool: Tool prefix (e.g., "HATCH_VCS", "SETUPTOOLS_SCM")
            env: Environment dict to read from (defaults to os.environ)

        Returns:
            GlobalOverrides instance ready to use as context manager
        """

        # Use EnvReader to read all environment variables with fallback
        reader = EnvReader(tools_names=(tool, "VCS_VERSIONING"), env=env)

        # Read debug flag - support multiple formats
        debug_val = reader.read("DEBUG")
        if debug_val is None:
            debug: int | Literal[False] = False
        else:
            # Try to parse as integer log level
            try:
                parsed_int = int(debug_val)
                # If it's a small integer (0, 1), treat as boolean flag
                # Otherwise treat as explicit log level (10, 20, 30, etc.)
                if parsed_int in (0, 1):
                    debug = logging.DEBUG if parsed_int else False
                else:
                    debug = parsed_int
            except ValueError:
                # Not an integer - check if it's a level name (DEBUG, INFO, WARNING, etc.)
                level_name = debug_val.upper()
                level_value = getattr(logging, level_name, None)
                if isinstance(level_value, int):
                    # Valid level name found
                    debug = level_value
                else:
                    # Unknown value - treat as boolean flag (any non-empty value means DEBUG)
                    debug = logging.DEBUG

        # Read subprocess timeout
        timeout_val = reader.read("SUBPROCESS_TIMEOUT")
        subprocess_timeout = 40  # default
        if timeout_val is not None:
            try:
                subprocess_timeout = int(timeout_val)
            except ValueError:
                log.warning(
                    "Invalid SUBPROCESS_TIMEOUT value '%s', using default %d",
                    timeout_val,
                    subprocess_timeout,
                )

        # Read hg command
        hg_command = reader.read("HG_COMMAND") or "hg"

        # Read SOURCE_DATE_EPOCH (standard env var, no prefix)
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

        return cls(
            debug=debug,
            subprocess_timeout=subprocess_timeout,
            hg_command=hg_command,
            source_date_epoch=source_date_epoch,
            tool=tool,
        )

    def __enter__(self) -> GlobalOverrides:
        """Enter context: set this as the active override."""
        token = _active_overrides.set(self)
        # Store the token so we can restore in __exit__
        object.__setattr__(self, "_token", token)
        return self

    def __exit__(self, *exc_info: Any) -> None:
        """Exit context: restore previous override state."""
        token = getattr(self, "_token", None)
        if token is not None:
            _active_overrides.reset(token)
            object.__delattr__(self, "_token")

    def log_level(self) -> int:
        """Get the appropriate logging level from the debug setting.

        Returns:
            logging level constant (DEBUG, WARNING, etc.)
        """
        if self.debug is False:
            return logging.WARNING
        return self.debug

    def source_epoch_or_utc_now(self) -> datetime:
        """Get datetime from SOURCE_DATE_EPOCH or current UTC time.

        Returns:
            datetime object in UTC timezone
        """
        from datetime import datetime, timezone

        if self.source_date_epoch is not None:
            return datetime.fromtimestamp(self.source_date_epoch, timezone.utc)
        else:
            return datetime.now(timezone.utc)

    @classmethod
    def from_active(cls, **changes: Any) -> GlobalOverrides:
        """Create a new GlobalOverrides instance based on the currently active one.

        Uses dataclasses.replace() to create a modified copy of the active overrides.
        If no overrides are currently active, raises a RuntimeError.

        Args:
            **changes: Fields to update in the new instance

        Returns:
            New GlobalOverrides instance with the specified changes

        Raises:
            RuntimeError: If no GlobalOverrides context is currently active

        Example:
            >>> with GlobalOverrides.from_env("TEST"):
            ...     # Create a modified version with different debug level
            ...     with GlobalOverrides.from_active(debug=logging.INFO):
            ...         # This context has INFO level instead
            ...         pass
        """
        from dataclasses import replace

        active = _active_overrides.get()
        if active is None:
            raise RuntimeError(
                "Cannot call from_active() without an active GlobalOverrides context. "
                "Use from_env() to create the initial context."
            )

        return replace(active, **changes)

    def export(self, target: MutableMapping[str, str] | MonkeyPatch) -> None:
        """Export overrides to environment variables.

        Can export to either a dict-like environment or a pytest monkeypatch fixture.
        This is useful for tests that need to propagate overrides to subprocesses.

        Args:
            target: Either a MutableMapping (e.g., dict, os.environ) or a pytest
                   MonkeyPatch instance (or any object with a setenv method)

        Example:
            >>> # Export to environment dict
            >>> overrides = GlobalOverrides.from_env("TEST", env={"TEST_DEBUG": "1"})
            >>> env = {}
            >>> overrides.export(env)
            >>> print(env["TEST_DEBUG"])
            1

            >>> # Export via pytest monkeypatch
            >>> def test_something(monkeypatch):
            ...     overrides = GlobalOverrides.from_env("TEST")
            ...     overrides.export(monkeypatch)
            ...     # Environment is now set
        """

        # Helper to set variable based on target type
        def set_var(key: str, value: str) -> None:
            if isinstance(target, MutableMapping):
                target[key] = value
            else:
                target.setenv(key, value)

        # Export SOURCE_DATE_EPOCH
        if self.source_date_epoch is not None:
            set_var("SOURCE_DATE_EPOCH", str(self.source_date_epoch))

        # Export tool-prefixed variables
        prefix = self.tool

        # Export debug
        if self.debug is False:
            set_var(f"{prefix}_DEBUG", "0")
        else:
            set_var(f"{prefix}_DEBUG", str(self.debug))

        # Export subprocess timeout
        set_var(f"{prefix}_SUBPROCESS_TIMEOUT", str(self.subprocess_timeout))

        # Export hg command
        set_var(f"{prefix}_HG_COMMAND", self.hg_command)


# Thread-local storage for active global overrides
_active_overrides: ContextVar[GlobalOverrides | None] = ContextVar(
    "vcs_versioning_overrides", default=None
)

# Flag to track if we've already warned about auto-creating context
_auto_create_warning_issued = False


# Accessor functions for getting current override values


def get_active_overrides() -> GlobalOverrides:
    """Get the currently active GlobalOverrides instance.

    If no context is active, creates one from the current environment
    using SETUPTOOLS_SCM prefix for legacy compatibility.

    Returns:
        GlobalOverrides instance
    """
    global _auto_create_warning_issued

    overrides = _active_overrides.get()
    if overrides is None:
        # Auto-create context from environment for backwards compatibility
        if not _auto_create_warning_issued:
            warnings.warn(
                "No GlobalOverrides context is active. "
                "Auto-creating one with SETUPTOOLS_SCM prefix for backwards compatibility. "
                "Consider using 'with GlobalOverrides.from_env(\"YOUR_TOOL\"):' explicitly.",
                UserWarning,
                stacklevel=2,
            )
            _auto_create_warning_issued = True
        overrides = GlobalOverrides.from_env("SETUPTOOLS_SCM")
    return overrides


def get_debug_level() -> int | Literal[False]:
    """Get current debug level from active override context.

    Returns:
        logging level constant (DEBUG, INFO, WARNING, etc.) or False
    """
    return get_active_overrides().debug


def get_subprocess_timeout() -> int:
    """Get current subprocess timeout from active override context.

    Returns:
        Subprocess timeout in seconds
    """
    return get_active_overrides().subprocess_timeout


def get_hg_command() -> str:
    """Get current Mercurial command from active override context.

    Returns:
        Mercurial command string
    """
    return get_active_overrides().hg_command


def get_source_date_epoch() -> int | None:
    """Get SOURCE_DATE_EPOCH from active override context.

    Returns:
        Unix timestamp or None
    """
    return get_active_overrides().source_date_epoch


def source_epoch_or_utc_now() -> datetime:
    """Get datetime from SOURCE_DATE_EPOCH or current UTC time.

    Uses the active GlobalOverrides context. If no SOURCE_DATE_EPOCH is set,
    returns the current UTC time.

    Returns:
        datetime object in UTC timezone
    """
    return get_active_overrides().source_epoch_or_utc_now()


__all__ = [
    "EnvReader",
    "GlobalOverrides",
    "get_active_overrides",
    "get_debug_level",
    "get_hg_command",
    "get_source_date_epoch",
    "get_subprocess_timeout",
    "source_epoch_or_utc_now",
]
