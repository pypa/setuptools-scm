from __future__ import annotations

import logging
import warnings
from collections.abc import Callable, Iterable, Iterator
from importlib import metadata as im
from importlib.metadata import EntryPoint
from typing import TYPE_CHECKING, Any, cast

from ._compat import entry_points

__all__ = [
    "entry_points",
    "im",
]
if TYPE_CHECKING:
    from . import _types as _t
    from ._config import Configuration, ParseFunction
    from ._scm_version import ScmVersion

log = logging.getLogger(__name__)


# These are the six plugin groups shared with older setuptools-scm releases.
_ALIASED_GROUPS = {
    "files_command",
    "files_command_fallback",
    "version_scheme",
    "local_scheme",
    "parse_scm",
    "parse_scm_fallback",
}


def iter_entry_points(group: str, *, name: str | None = None) -> Iterator[EntryPoint]:
    def registered(group_name: str) -> Iterable[EntryPoint]:
        if name is None:
            return entry_points(group=group_name)
        return entry_points(group=group_name, name=name)

    prefix, _, hook = group.partition(".")
    if (
        prefix not in {"vcs_versioning", "setuptools_scm"}
        or hook not in _ALIASED_GROUPS
    ):
        yield from registered(group)
        return

    canonical: set[tuple[str, str]] = set()
    for ep in registered(f"vcs_versioning.{hook}"):
        canonical.add((ep.name, ep.value))
        yield ep
    for ep in registered(f"setuptools_scm.{hook}"):
        if (ep.name, ep.value) not in canonical:
            yield ep


def load_entry_point(ep: EntryPoint) -> Any:
    prefix, _, hook = ep.group.partition(".")
    if prefix == "setuptools_scm" and hook in _ALIASED_GROUPS:
        warnings.warn(
            f"The {ep.group!r} entry-point group is deprecated. "
            f"Register {ep.name!r} under 'vcs_versioning.{hook}' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
    return ep.load()


def version_from_entrypoint(
    config: Configuration, *, entrypoint: str, root: _t.PathT
) -> ScmVersion | None:
    from ._discover import iter_matching_entrypoints

    log.debug("version_from_ep %s in %s", entrypoint, root)
    for ep in iter_matching_entrypoints(root, entrypoint, config):
        fn: ParseFunction = load_entry_point(ep)
        maybe_version: ScmVersion | None = fn(root, config=config)
        log.debug("%s found %r", ep, maybe_version)
        if maybe_version is not None:
            return maybe_version
    return None


def _get_ep(group: str, name: str) -> Any | None:
    for ep in iter_entry_points(group, name=name):
        log.debug("ep found: %s", ep.name)
        return load_entry_point(ep)
    return None


def _get_from_object_reference_str(path: str, group: str) -> Any | None:
    # todo: remove for importlib native spelling
    ep = EntryPoint(path, path, group)
    try:
        return ep.load()
    except (AttributeError, ModuleNotFoundError):
        return None


def _iter_version_schemes(
    entrypoint: str,
    scheme_value: _t.VERSION_SCHEMES,
    _memo: set[object] | None = None,
) -> Iterator[Callable[[ScmVersion], str | None]]:
    if _memo is None:
        _memo = set()
    if isinstance(scheme_value, str):
        scheme_value = cast(
            "_t.VERSION_SCHEMES",
            _get_ep(entrypoint, scheme_value)
            or _get_from_object_reference_str(scheme_value, entrypoint),
        )

    if isinstance(scheme_value, (list, tuple)):
        for variant in scheme_value:
            if variant not in _memo:
                _memo.add(variant)
                yield from _iter_version_schemes(entrypoint, variant, _memo=_memo)
    elif callable(scheme_value):
        yield scheme_value


def _call_version_scheme(
    version: ScmVersion,
    entrypoint: str,
    given_value: _t.VERSION_SCHEMES,
    default: str | None = None,
) -> str:
    found_any_implementation = False
    for scheme in _iter_version_schemes(entrypoint, given_value):
        found_any_implementation = True
        result = scheme(version)
        if result is not None:
            return result
    if not found_any_implementation:
        raise ValueError(
            f'Couldn\'t find any implementations for entrypoint "{entrypoint}"'
            f' with value "{given_value}".'
        )
    if default is not None:
        return default
    raise ValueError(
        f'None of the "{entrypoint}" entrypoints matching "{given_value}"'
        " returned a value."
    )
