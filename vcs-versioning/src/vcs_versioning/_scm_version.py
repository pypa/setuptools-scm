"""Core ScmVersion data structure and parsing utilities.

This module contains the ScmVersion class which represents a parsed version
from source control metadata, along with utilities for creating and parsing
ScmVersion objects.
"""

from __future__ import annotations

import dataclasses
import logging
import warnings
from collections.abc import Callable
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Concatenate, ParamSpec, TypedDict

from . import _config
from . import _version_cls as _v
from ._node_utils import _format_node_for_output
from ._version_cls import _Version

if TYPE_CHECKING:
    import sys

    if sys.version_info >= (3, 11):
        from typing import Unpack
    else:
        from typing_extensions import Unpack

_P = ParamSpec("_P")

log = logging.getLogger(__name__)


class _TagDict(TypedDict):
    version: str
    prefix: str
    suffix: str


class VersionExpectations(TypedDict, total=False):
    """Expected properties for ScmVersion matching."""

    tag: str | _Version
    distance: int
    dirty: bool
    node_prefix: str  # Prefix of the node/commit hash
    branch: str | None
    exact: bool
    preformatted: bool
    node_date: date | None
    time: datetime | None


@dataclasses.dataclass
class mismatches:
    """Represents mismatches between expected and actual ScmVersion properties."""

    expected: dict[str, Any]
    actual: dict[str, Any]

    def __bool__(self) -> bool:
        """mismatches is falsy to allow `if not version.matches(...)`."""
        return False

    def __str__(self) -> str:
        """Format mismatches for error reporting."""
        lines = []
        for key, exp_val in self.expected.items():
            if key == "node_prefix":
                # Special handling for node prefix matching
                actual_node = self.actual.get("node")
                if not actual_node or not actual_node.startswith(exp_val):
                    lines.append(
                        f"  node: expected prefix '{exp_val}', got '{actual_node}'"
                    )
            else:
                act_val = self.actual.get(key)
                if str(exp_val) != str(act_val):
                    lines.append(f"  {key}: expected {exp_val!r}, got {act_val!r}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"mismatches(expected={self.expected!r}, actual={self.actual!r})"


def _parse_version_tag(
    tag: str | object, config: _config.Configuration
) -> _TagDict | None:
    match = config.tag_regex.match(str(tag))

    if match:
        key: str | int = 1 if len(match.groups()) == 1 else "version"
        full = match.group(0)
        log.debug("%r %r %s", tag, config.tag_regex, match)
        log.debug(
            "key %s data %s, %s, %r", key, match.groupdict(), match.groups(), full
        )

        if version := match.group(key):
            result = _TagDict(
                version=version,
                prefix=full[: match.start(key)],
                suffix=full[match.end(key) :],
            )

            log.debug("tag %r parsed to %r", tag, result)
            return result

        raise ValueError(
            f'The tag_regex "{config.tag_regex.pattern}" matched tag "{tag}", '
            "however the matched group has no value."
        )
    else:
        log.debug("tag %r did not parse", tag)

        return None


def callable_or_entrypoint(group: str, callable_or_name: str | Any) -> Any:
    log.debug("ep %r %r", group, callable_or_name)

    if callable(callable_or_name):
        return callable_or_name

    from ._entrypoints import _get_ep

    return _get_ep(group, callable_or_name)


def tag_to_version(
    tag: _Version | str, config: _config.Configuration
) -> _Version | None:
    """
    take a tag that might be prefixed with a keyword and return only the version part
    """
    log.debug("tag %s", tag)

    tag_dict = _parse_version_tag(tag, config)
    if tag_dict is None or not tag_dict.get("version", None):
        warnings.warn(f"tag {tag!r} no version found", stacklevel=2)
        return None

    version_str = tag_dict["version"]
    log.debug("version pre parse %s", version_str)

    # Try to create version from base version first
    try:
        version: _Version = config.version_cls(version_str)
        log.debug("version=%r", version)
    except Exception:
        warnings.warn(
            f"tag {tag!r} will be stripped of its suffix {tag_dict.get('suffix', '')!r}",
            stacklevel=2,
        )
        # Fall back to trying without any suffix
        version = config.version_cls(version_str)
        log.debug("version=%r", version)
        return version

    # If base version is valid, check if we can preserve the suffix
    if suffix := tag_dict.get("suffix", ""):
        log.debug("tag %r includes local build data %r, preserving it", tag, suffix)
        # Try creating version with suffix - if it fails, we'll use the base version
        try:
            version_with_suffix: _Version = config.version_cls(version_str + suffix)
            log.debug("version with suffix=%r", version_with_suffix)
            return version_with_suffix
        except Exception:
            warnings.warn(
                f"tag {tag!r} will be stripped of its suffix {suffix!r}", stacklevel=2
            )
            # Return the base version without suffix
            return version

    return version


def _source_epoch_or_utc_now() -> datetime:
    """Get datetime from SOURCE_DATE_EPOCH or current UTC time.

    Uses the active GlobalOverrides context if available, otherwise returns
    current UTC time.
    """
    from .overrides import source_epoch_or_utc_now

    return source_epoch_or_utc_now()


@dataclasses.dataclass
class ScmVersion:
    """represents a parsed version from scm"""

    tag: _v.Version | _v.NonNormalizedVersion
    """the related tag or preformatted version"""
    config: _config.Configuration
    """the configuration used to parse the version"""
    distance: int = 0
    """the number of commits since the tag"""
    node: str | None = None
    """the shortened node id"""
    dirty: bool = False
    """whether the working copy had uncommitted changes"""
    preformatted: bool = False
    """whether the version string was preformatted"""
    branch: str | None = None
    """the branch name if any"""
    node_date: date | None = None
    """the date of the commit if available"""
    time: datetime = dataclasses.field(default_factory=_source_epoch_or_utc_now)
    """the current time or source epoch time
    only set for unit-testing version schemes
    for real usage it must be `now(utc)` or `SOURCE_EPOCH`
    """

    @property
    def exact(self) -> bool:
        """returns true checked out exactly on a tag and no local changes apply"""
        return self.distance == 0 and not self.dirty

    @property
    def short_node(self) -> str | None:
        """Return the node formatted for output."""
        return _format_node_for_output(self.node)

    def __repr__(self) -> str:
        return (
            f"<ScmVersion {self.tag} dist={self.distance} "
            f"node={self.node} dirty={self.dirty} branch={self.branch}>"
        )

    def format_with(self, fmt: str, **kw: object) -> str:
        """format a given format string with attributes of this object"""
        return fmt.format(
            time=self.time,
            tag=self.tag,
            distance=self.distance,
            node=_format_node_for_output(self.node),
            dirty=self.dirty,
            branch=self.branch,
            node_date=self.node_date,
            **kw,
        )

    def format_choice(self, clean_format: str, dirty_format: str, **kw: object) -> str:
        """given `clean_format` and `dirty_format`

        choose one based on `self.dirty` and format it using `self.format_with`"""

        return self.format_with(dirty_format if self.dirty else clean_format, **kw)

    def format_next_version(
        self,
        guess_next: Callable[Concatenate[ScmVersion, _P], str],
        fmt: str = "{guessed}.dev{distance}",
        *k: _P.args,
        **kw: _P.kwargs,
    ) -> str:
        guessed = guess_next(self, *k, **kw)
        return self.format_with(fmt, guessed=guessed)

    def matches(self, **expectations: Unpack[VersionExpectations]) -> bool | mismatches:
        """Check if this ScmVersion matches the given expectations.

        Returns True if all specified properties match, or a mismatches
        object (which is falsy) containing details of what didn't match.

        Args:
            **expectations: Properties to check, using VersionExpectations TypedDict
        """
        # Map expectation keys to ScmVersion attributes
        attr_map: dict[str, Callable[[], Any]] = {
            "tag": lambda: str(self.tag),
            "node_prefix": lambda: self.node,
            "distance": lambda: self.distance,
            "dirty": lambda: self.dirty,
            "branch": lambda: self.branch,
            "exact": lambda: self.exact,
            "preformatted": lambda: self.preformatted,
            "node_date": lambda: self.node_date,
            "time": lambda: self.time,
        }

        # Build actual values dict
        actual: dict[str, Any] = {
            key: attr_map[key]() for key in expectations if key in attr_map
        }

        # Process expectations
        expected = {
            "tag" if k == "tag" else k: str(v) if k == "tag" else v
            for k, v in expectations.items()
        }

        # Check for mismatches
        def has_mismatch() -> bool:
            for key, exp_val in expected.items():
                if key == "node_prefix":
                    act_val = actual.get("node_prefix")
                    if not act_val or not act_val.startswith(exp_val):
                        return True
                else:
                    if str(exp_val) != str(actual.get(key)):
                        return True
            return False

        if has_mismatch():
            # Rename node_prefix back to node for actual values in mismatch reporting
            if "node_prefix" in actual:
                actual["node"] = actual.pop("node_prefix")
            return mismatches(expected=expected, actual=actual)
        return True


def _parse_tag(
    tag: _Version | str, preformatted: bool, config: _config.Configuration
) -> _Version:
    if preformatted:
        # For preformatted versions, tag should already be validated as a version object
        # String validation is handled in meta function before calling this
        if isinstance(tag, str):
            # This should not happen with enhanced meta, but kept for safety
            return _v.NonNormalizedVersion(tag)
        else:
            # Already a version object (including test mocks), return as-is
            return tag
    elif not isinstance(tag, config.version_cls):
        version = tag_to_version(tag, config)
        assert version is not None
        return version
    else:
        return tag


class _ScmVersionKwargs(TypedDict, total=False):
    """TypedDict for ScmVersion constructor keyword arguments."""

    distance: int
    node: str | None
    dirty: bool
    preformatted: bool
    branch: str | None
    node_date: date | None
    time: datetime


def meta(
    tag: str | _Version,
    *,
    distance: int = 0,
    dirty: bool = False,
    node: str | None = None,
    preformatted: bool = False,
    branch: str | None = None,
    config: _config.Configuration,
    node_date: date | None = None,
    time: datetime | None = None,
) -> ScmVersion:
    parsed_version: _Version
    # Enhanced string validation for preformatted versions
    if preformatted and isinstance(tag, str):
        # Validate PEP 440 compliance using NonNormalizedVersion
        # Let validation errors bubble up to the caller
        parsed_version = _v.NonNormalizedVersion(tag)
    else:
        # Use existing _parse_tag logic for non-preformatted or already validated inputs
        parsed_version = _parse_tag(tag, preformatted, config)

    log.info("version %s -> %s", tag, parsed_version)
    assert parsed_version is not None, f"Can't parse version {tag}"

    # Pass time explicitly to avoid triggering default_factory if provided
    kwargs: _ScmVersionKwargs = {
        "distance": distance,
        "node": node,
        "dirty": dirty,
        "preformatted": preformatted,
        "branch": branch,
        "node_date": node_date,
    }
    if time is not None:
        kwargs["time"] = time

    scm_version = ScmVersion(parsed_version, config=config, **kwargs)
    return scm_version
