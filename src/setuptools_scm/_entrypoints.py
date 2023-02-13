from __future__ import annotations

import warnings
from typing import Any
from typing import Callable
from typing import cast
from typing import Iterator
from typing import overload
from typing import TYPE_CHECKING

from . import version
from .utils import trace

if TYPE_CHECKING:
    from ._config import Configuration
    from typing_extensions import Protocol
    from . import _types as _t
else:
    Configuration = Any

    class Protocol:
        pass


def _version_from_entrypoints(
    config: Configuration, fallback: bool = False
) -> version.ScmVersion | None:
    if fallback:
        entrypoint = "setuptools_scm.parse_scm_fallback"
        root = config.fallback_root
    else:
        entrypoint = "setuptools_scm.parse_scm"
        root = config.absolute_root

    from .discover import iter_matching_entrypoints

    trace("version_from_ep", entrypoint, root)
    for ep in iter_matching_entrypoints(root, entrypoint, config):
        fn = ep.load()
        maybe_version: version.ScmVersion | None = fn(root, config=config)
        trace(ep, version)
        if maybe_version is not None:
            return maybe_version
    return None


try:
    from importlib.metadata import entry_points  # type: ignore
except ImportError:
    try:
        from importlib_metadata import entry_points
    except ImportError:
        from collections import defaultdict

        def entry_points() -> dict[str, list[_t.EntrypointProtocol]]:
            warnings.warn(
                "importlib metadata missing, "
                "this may happen at build time for python3.7"
            )
            return defaultdict(list)


def iter_entry_points(
    group: str, name: str | None = None
) -> Iterator[_t.EntrypointProtocol]:
    all_eps = entry_points()
    if hasattr(all_eps, "select"):
        eps = all_eps.select(group=group)
    else:
        eps = all_eps[group]
    if name is None:
        return iter(eps)
    return (ep for ep in eps if ep.name == name)


def _get_ep(group: str, name: str) -> Any | None:
    from ._entrypoints import iter_entry_points

    for ep in iter_entry_points(group, name):
        trace("ep found:", ep.name)
        return ep.load()
    else:
        return None


def _get_from_object_reference_str(path: str) -> Any | None:
    try:
        from importlib.metadata import EntryPoint
    except ImportError:
        from importlib_metadata import EntryPoint
    try:
        return EntryPoint(path, path, None).load()
    except (AttributeError, ModuleNotFoundError):
        return None


def _iter_version_schemes(
    entrypoint: str,
    scheme_value: _t.VERSION_SCHEMES,
    _memo: set[object] | None = None,
) -> Iterator[Callable[[version.ScmVersion], str]]:
    if _memo is None:
        _memo = set()
    if isinstance(scheme_value, str):
        scheme_value = cast(
            "_t.VERSION_SCHEMES",
            _get_ep(entrypoint, scheme_value)
            or _get_from_object_reference_str(scheme_value),
        )

    if isinstance(scheme_value, (list, tuple)):
        for variant in scheme_value:
            if variant not in _memo:
                _memo.add(variant)
                yield from _iter_version_schemes(entrypoint, variant, _memo=_memo)
    elif callable(scheme_value):
        yield scheme_value


@overload
def _call_version_scheme(
    version: version.ScmVersion, entypoint: str, given_value: str, default: str
) -> str:
    ...


@overload
def _call_version_scheme(
    version: version.ScmVersion, entypoint: str, given_value: str, default: None
) -> str | None:
    ...


def _call_version_scheme(
    version: version.ScmVersion, entypoint: str, given_value: str, default: str | None
) -> str | None:
    for scheme in _iter_version_schemes(entypoint, given_value):
        result = scheme(version)
        if result is not None:
            return result
    return default
