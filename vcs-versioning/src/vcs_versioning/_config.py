"""configuration"""

from __future__ import annotations

import dataclasses
import logging
import os
import re
import warnings
from collections.abc import Mapping
from pathlib import Path
from re import Pattern
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from ._backends import _git
    from ._backends._scm_workdir import ScmWorkdir
    from ._environment import VcsEnvironment
    from ._fallback_workdir import FallbackWorkdir

from . import _types as _t
from ._overrides import read_toml_overrides
from ._paths import resolve_paths
from ._pyproject_reading import PyProjectData, get_args_for_pyproject, read_pyproject
from ._version_cls import Version as _Version
from ._version_cls import _validate_version_cls
from ._version_cls import _Version as _VersionAlias

log = logging.getLogger(__name__)


def _is_called_from_dataclasses() -> bool:
    """Check if the current call is from the dataclasses module."""
    import inspect

    frame = inspect.currentframe()
    try:
        # Walk up to 7 frames to check for dataclasses calls
        current_frame = frame
        assert current_frame is not None
        for _ in range(7):
            current_frame = current_frame.f_back
            if current_frame is None:
                break
            if "dataclasses.py" in current_frame.f_code.co_filename:
                return True
        return False
    finally:
        del frame


class _GitDescribeCommandDescriptor:
    """Data descriptor for deprecated git_describe_command field."""

    def __get__(
        self, obj: Configuration | None, objtype: type[Configuration] | None = None
    ) -> _t.CMD_TYPE | None:
        if obj is None:
            return self  # type: ignore[return-value]

        # Only warn if not being called by dataclasses.replace or similar introspection
        is_from_dataclasses = _is_called_from_dataclasses()
        if not is_from_dataclasses:
            warnings.warn(
                "Configuration field 'git_describe_command' is deprecated. "
                "Use 'scm.git.describe_command' instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        return obj.scm.git.describe_command

    def __set__(self, obj: Configuration, value: _t.CMD_TYPE | None) -> None:
        warnings.warn(
            "Configuration field 'git_describe_command' is deprecated. "
            "Use 'scm.git.describe_command' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        obj.scm.git.describe_command = value


DEFAULT_TAG_REGEX = re.compile(
    r"^(?:[\w-]+-)?(?P<version>[vV]?\d+(?:\.\d+){0,2}[^\+]*)(?:\+.*)?$"
)
"""default tag regex that tries to match PEP440 style versions
with prefix consisting of dashed words"""

DEFAULT_VERSION_SCHEME = "guess-next-dev"
DEFAULT_LOCAL_SCHEME = "node-and-date"


def _check_tag_regex(value: str | Pattern[str] | None) -> Pattern[str]:
    if not value:
        regex = DEFAULT_TAG_REGEX
    else:
        regex = re.compile(value)

    group_names = regex.groupindex.keys()
    if regex.groups == 0 or (regex.groups > 1 and "version" not in group_names):
        raise ValueError(
            f"Expected tag_regex '{regex.pattern}' to contain a single match group or"
            " a group named 'version' to identify the version part of any tag."
        )

    return regex


def _get_default_git_pre_parse() -> _git.GitPreParse:
    """Get the default git pre_parse enum value"""
    from ._backends import _git

    return _git.GitPreParse.WARN_ON_SHALLOW


class ParseFunction(Protocol):
    def __call__(
        self, root: _t.PathT, *, config: Configuration
    ) -> _t.SCMVERSION | None: ...


@dataclasses.dataclass
class GitConfiguration:
    """Git-specific configuration options"""

    pre_parse: _git.GitPreParse = dataclasses.field(
        default_factory=lambda: _get_default_git_pre_parse()
    )
    describe_command: _t.CMD_TYPE | None = None

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> GitConfiguration:
        """Create GitConfiguration from configuration data, converting strings to enums"""
        git_data = data.copy()

        # Convert string pre_parse values to enum instances
        if "pre_parse" in git_data and isinstance(git_data["pre_parse"], str):
            from ._backends import _git

            try:
                git_data["pre_parse"] = _git.GitPreParse(git_data["pre_parse"])
            except ValueError as e:
                valid_options = [option.value for option in _git.GitPreParse]
                raise ValueError(
                    f"Invalid git pre_parse function '{git_data['pre_parse']}'. "
                    f"Valid options are: {', '.join(valid_options)}"
                ) from e

        return cls(**git_data)


@dataclasses.dataclass
class TagConfiguration:
    """Tag matching configuration options.

    Controls which VCS tags are considered version tags and how they are parsed.
    """

    prefix: str = ""
    """Literal prefix that version tags must start with.

    The prefix is used to filter tags in ``git describe --match`` and is
    stripped before version parsing.  For monorepos, set this to e.g.
    ``"hatchling-v"`` so only ``hatchling-v1.0.0`` style tags are considered.
    """

    strict: bool | None = None
    """Tri-state strictness for version-like tag matching.

    - ``None`` (default): permissive ``*[0-9]*`` matching with a
      ``FutureWarning`` that the default will change to ``True``.
    - ``True``: strict — tags must contain at least one dot
      (e.g. ``*[0-9]*.*[0-9]*``), rejecting event-style tags.
    - ``False``: explicitly permissive, no warning.
    """

    regex: Pattern[str] = DEFAULT_TAG_REGEX
    """Regex applied after ``git describe`` to extract the version from a tag.

    Must contain either a single capture group or a named group ``version``.
    The new canonical location for what was previously ``tag_regex`` at the
    top level of the configuration.
    """

    def __post_init__(self) -> None:
        self.regex = _check_tag_regex(self.regex)

    def describe_match_glob(self) -> str:
        """Build the ``git describe --match`` glob from prefix + strict."""
        if self.strict:
            version_glob = "*[0-9]*.*[0-9]*"
        else:
            version_glob = "*[0-9]*"
        return f"{self.prefix}{version_glob}"

    @classmethod
    def from_data(cls, data: dict[str, Any] | None) -> TagConfiguration:
        """Create TagConfiguration from configuration data."""
        if data is None:
            return cls()
        tag_data = data.copy()
        if "regex" in tag_data and isinstance(tag_data["regex"], str):
            tag_data["regex"] = re.compile(tag_data["regex"])
        return cls(**tag_data)


_SENTINEL_TAG_CONFIG = TagConfiguration()


class _TagRegexDescriptor:
    """Data descriptor for deprecated top-level tag_regex field.

    Proxies reads/writes to ``tag.regex`` and emits ``DeprecationWarning``.
    """

    def __get__(
        self, obj: Configuration | None, objtype: type[Configuration] | None = None
    ) -> Pattern[str]:
        if obj is None:
            return self  # type: ignore[return-value]

        if not _is_called_from_dataclasses():
            warnings.warn(
                "Configuration field 'tag_regex' is deprecated. "
                "Use 'tag.regex' instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        return obj.tag.regex

    def __set__(self, obj: Configuration, value: str | Pattern[str]) -> None:
        warnings.warn(
            "Configuration field 'tag_regex' is deprecated. Use 'tag.regex' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        obj.tag.regex = _check_tag_regex(value)


@dataclasses.dataclass
class ScmConfiguration:
    """SCM-specific configuration options"""

    git: GitConfiguration = dataclasses.field(default_factory=GitConfiguration)

    @classmethod
    def from_data(cls, data: dict[str, Any] | None) -> ScmConfiguration:
        """Create ScmConfiguration from configuration data"""
        if data is None:
            return cls()
        scm_data = data.copy()

        # Handle git-specific configuration
        git_data = scm_data.pop("git", {})
        git_config = GitConfiguration.from_data(git_data)

        return cls(git=git_config, **scm_data)


@dataclasses.dataclass
class Configuration:
    """Global configuration model"""

    relative_to: _t.PathT | None = None
    root: _t.PathT = "."
    version_scheme: _t.VERSION_SCHEMES = DEFAULT_VERSION_SCHEME
    local_scheme: _t.VERSION_SCHEMES = DEFAULT_LOCAL_SCHEME
    tag_regex: dataclasses.InitVar[str | Pattern[str] | None] = _TagRegexDescriptor()
    parentdir_prefix_version: str | None = None
    fallback_version: str | None = None
    fallback_root: _t.PathT = "."
    write_to: _t.PathT | None = None
    write_to_template: str | None = None
    version_file: _t.PathT | None = None
    version_file_template: str | None = None
    parse: ParseFunction | None = None
    git_describe_command: dataclasses.InitVar[_t.CMD_TYPE | None] = (
        _GitDescribeCommandDescriptor()
    )

    dist_name: str | None = None
    version_cls: type[_VersionAlias] = _Version
    search_parent_directories: bool = False
    project_path: str | None = None

    parent: _t.PathT | None = None

    write_to_source: bool | None = None
    """Whether to write version files to the source tree at inference time.

    - ``None`` (default): write to source **and** emit a ``DeprecationWarning``
      telling users to set this explicitly, since the default will change
      in the next major release.
    - ``True``: write to source tree, no warning.
    - ``False``: do **not** write to source tree, no warning.

    The ``SETUPTOOLS_SCM_WRITE_TO_SOURCE`` / ``VCS_VERSIONING_WRITE_TO_SOURCE``
    environment variable overrides this setting.
    """

    # Nested configurations
    tag: TagConfiguration = dataclasses.field(
        default_factory=lambda: TagConfiguration()
    )
    scm: ScmConfiguration = dataclasses.field(
        default_factory=lambda: ScmConfiguration()
    )

    _env: VcsEnvironment | None = dataclasses.field(
        default=None, repr=False, compare=False
    )
    """The :class:`~vcs_versioning._environment.VcsEnvironment` for this config.

    Populated by ``VcsEnvironment.build_config()`` or lazily on first
    ``env`` access (with a ``DeprecationWarning``).  ``None`` until then.
    """

    # Deprecated fields (handled in __post_init__)

    def __post_init__(
        self,
        tag_regex: str | Pattern[str] | None,
        git_describe_command: _t.CMD_TYPE | None,
    ) -> None:
        # Handle deprecated top-level tag_regex
        if tag_regex is not None and not isinstance(tag_regex, _TagRegexDescriptor):
            is_from_dataclasses = _is_called_from_dataclasses()
            same_value = tag_regex == self.tag.regex or (
                isinstance(tag_regex, Pattern)
                and tag_regex.pattern == self.tag.regex.pattern
            )
            if is_from_dataclasses and same_value:
                pass
            else:
                warnings.warn(
                    "Configuration field 'tag_regex' is deprecated. "
                    "Use 'tag.regex' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                if self.tag.regex.pattern != DEFAULT_TAG_REGEX.pattern:
                    raise ValueError(
                        "Cannot specify both 'tag_regex' (deprecated) and "
                        "'tag.regex'. Please use only 'tag.regex'."
                    )
                # Replace with a new TagConfiguration to avoid mutating shared objects
                self.tag = dataclasses.replace(
                    self.tag, regex=_check_tag_regex(tag_regex)
                )

        if self.tag.strict is None:
            warnings.warn(
                "tag.strict is not set. Currently defaults to False (permissive "
                "tag matching). In a future major version the default will change "
                "to True (require tags to contain a dot). "
                "Set tag.strict = true or tag.strict = false explicitly in your "
                "[tool.setuptools_scm] / [tool.vcs-versioning] config to silence "
                "this warning.",
                FutureWarning,
                stacklevel=2,
            )

        if (
            self.tag.prefix or self.tag.strict is not None
        ) and self.scm.git.describe_command is not None:
            warnings.warn(
                "Both tag.prefix/tag.strict and scm.git.describe_command are set. "
                "The explicit describe_command takes precedence; tag.prefix and "
                "tag.strict will have no effect on the git describe match pattern.",
                UserWarning,
                stacklevel=2,
            )

        self._resolved_paths = resolve_paths(
            relative_to=self.relative_to,
            root=self.root,
            project_path=self.project_path,
        )
        if self.project_path is None and self._resolved_paths.project_path is not None:
            self.project_path = self._resolved_paths.project_path

        # Handle deprecated git_describe_command
        # Check if it's a descriptor object (happens when no value is passed)
        if git_describe_command is not None and not isinstance(
            git_describe_command, _GitDescribeCommandDescriptor
        ):
            # Check if this is being called from dataclasses
            is_from_dataclasses = _is_called_from_dataclasses()

            same_value = (
                self.scm.git.describe_command is not None
                and self.scm.git.describe_command == git_describe_command
            )

            if is_from_dataclasses and same_value:
                # Ignore the passed value - it's from dataclasses.replace() with same value
                pass
            else:
                warnings.warn(
                    "Configuration field 'git_describe_command' is deprecated. "
                    "Use 'scm.git.describe_command' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                # Check for conflicts
                if self.scm.git.describe_command is not None:
                    raise ValueError(
                        "Cannot specify both 'git_describe_command' (deprecated) and "
                        "'scm.git.describe_command'. Please use only 'scm.git.describe_command'."
                    )
                self.scm.git.describe_command = git_describe_command

    @property
    def absolute_root(self) -> str:
        return str(self._resolved_paths.scm_probe_root)

    @property
    def env(self) -> VcsEnvironment:
        """The :class:`~vcs_versioning._environment.VcsEnvironment` for this config.

        Always non-None after first access — set by ``VcsEnvironment.build_config()``
        or lazily resolved on first access (with a ``DeprecationWarning``).
        """
        if self._env is None:
            warnings.warn(
                "Configuration was created without VcsEnvironment. "
                "Use VcsEnvironment.build_config() to create configurations "
                "with runtime settings attached explicitly. "
                "This will become an error in vcs-versioning 2.0.",
                DeprecationWarning,
                stacklevel=2,
            )
            from ._environment import resolve_runtime_env

            object.__setattr__(self, "_env", resolve_runtime_env())
        assert self._env is not None
        return self._env

    def discover_workdir(self) -> ScmWorkdir | FallbackWorkdir | None:
        """Discover the workdir for this configuration."""
        from ._worktree_discovery import discover_workdir

        return discover_workdir(self)

    @classmethod
    def from_file(
        cls,
        name: str | os.PathLike[str] = "pyproject.toml",
        dist_name: str | None = None,
        pyproject_data: PyProjectData | None = None,
        *,
        tool_names: tuple[str, ...] | None = None,
        env: Mapping[str, str] | None = None,
        _env: VcsEnvironment | None = None,
        **kwargs: Any,
    ) -> Configuration:
        """
                Read Configuration from pyproject.toml (or similar).
                Raises exceptions when file is not found or toml is
                not installed or the file has invalid format.

        Parameters:
        - name: path to pyproject.toml
        - dist_name: name of the distribution
        - tool_names: env-var prefix order for TOML overrides
        - env: environment mapping for TOML overrides (default: os.environ)
        - _env: VcsEnvironment to attach to the resulting Configuration
        - **kwargs: additional keyword arguments to pass to the Configuration constructor
        """

        if pyproject_data is None:
            pyproject_data = read_pyproject(Path(name))
        args = get_args_for_pyproject(pyproject_data, dist_name, kwargs)

        # Per-project overrides: lower priority than env overrides
        from ._project_overrides import read_project_overrides

        relative_to = args.pop("relative_to", name)
        resolved = resolve_paths(
            relative_to=relative_to,
            root=args.get("root", "."),
            project_path=args.get("project_path"),
        )
        project_overrides = read_project_overrides(
            scm_root=resolved.scm_probe_root,
            project_path=resolved.project_path or "",
        )
        args.update(project_overrides)

        # Env overrides: highest priority
        args.update(
            read_toml_overrides(args["dist_name"], tool_names=tool_names, env=env)
        )
        return cls.from_data(relative_to=relative_to, data=args, _env=_env)

    @classmethod
    def from_data(
        cls,
        relative_to: str | os.PathLike[str],
        data: dict[str, Any],
        _env: VcsEnvironment | None = None,
    ) -> Configuration:
        """
        given configuration data
        create a config instance after validating tag regex/version class
        """
        version_cls = _validate_version_cls(
            data.pop("version_cls", None), data.pop("normalize", True)
        )

        # Migrate top-level tag_regex into tag.regex
        tag_data = data.pop("tag", None) or {}
        top_level_tag_regex = data.pop("tag_regex", None)
        if top_level_tag_regex is not None:
            if "regex" in tag_data:
                raise ValueError(
                    "Cannot specify both 'tag_regex' (deprecated) and "
                    "'tag.regex'. Please use only 'tag.regex'."
                )
            warnings.warn(
                "Configuration key 'tag_regex' is deprecated. Use 'tag.regex' instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            tag_data["regex"] = top_level_tag_regex

        tag_config = TagConfiguration.from_data(tag_data if tag_data else None)
        scm_data = data.pop("scm", {})
        scm_config = ScmConfiguration.from_data(scm_data)
        return cls(
            relative_to=relative_to,
            version_cls=version_cls,
            tag=tag_config,
            scm=scm_config,
            _env=_env,
            **data,
        )


_DEPRECATED_LEGACY_ATTRS: frozenset[str] = frozenset(
    {
        "absolute_root",
        "relative_to",
        "root",
    }
)


@dataclasses.dataclass(frozen=True)
class FrozenLegacyConfig:
    """Read-only view of Configuration for backward-compatible code paths.

    Wraps a ``Configuration`` and emits ``DeprecationWarning`` on first
    attribute access for fields that are being migrated to new APIs.
    Frozen dataclass -- all attributes are immutable.

    Use ``FrozenLegacyConfig(config)`` in legacy code paths that receive
    a config but should be guided toward the new explicit API chain.
    """

    _config: Configuration = dataclasses.field(repr=False)
    _warned: set[str] = dataclasses.field(
        default_factory=set, repr=False, compare=False, hash=False
    )

    def __getattr__(self, name: str) -> Any:
        if name in _DEPRECATED_LEGACY_ATTRS and name not in self._warned:
            self._warned.add(name)
            warnings.warn(
                f"Accessing '{name}' on legacy config view is deprecated. "
                f"Use ResolvedPaths or the new explicit API chain instead. "
                f"This will become an error in vcs-versioning 2.0.",
                DeprecationWarning,
                stacklevel=2,
            )
        return getattr(self._config, name)
