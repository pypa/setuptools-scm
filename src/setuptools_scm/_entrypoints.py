from __future__ import annotations

import sys

from typing import TYPE_CHECKING
from typing import Any
from typing import Callable
from typing import Iterator
from typing import cast
from typing import overload

from . import _log
from . import version

__all__ = [
    "entry_points",
    "im",
]
if TYPE_CHECKING:
    from . import _types as _t
    from ._config import Configuration
    from ._config import ParseFunction

    if sys.version_info[:2] < (3, 10):
        import importlib_metadata as im
    else:
        from importlib import metadata as im


log = _log.log.getChild("entrypoints")


def entry_points(**kw: Any) -> im.EntryPoints:
    if sys.version_info[:2] < (3, 10):
        import importlib_metadata as im
    else:
        import importlib.metadata as im

    return im.entry_points(**kw)


def version_from_entrypoint(
    config: Configuration, *, entrypoint: str, root: _t.PathT
) -> version.ScmVersion | None:
    from .discover import iter_matching_entrypoints

    log.debug("version_from_ep %s in %s", entrypoint, root)
    for ep in iter_matching_entrypoints(root, entrypoint, config):
        fn: ParseFunction = ep.load()
        maybe_version: version.ScmVersion | None = fn(root, config=config)
        log.debug("%s found %r", ep, maybe_version)
        if maybe_version is not None:
            return maybe_version
    return None


def _get_ep(group: str, name: str) -> Any | None:
    for ep in entry_points(group=group, name=name):
        log.debug("ep found: %s", ep.name)
        return ep.load()
    return None


def _get_from_object_reference_str(path: str, group: str) -> Any | None:
    # todo: remove for importlib native spelling
    from importlib.metadata import EntryPoint  # hack

    ep = EntryPoint(path, path, group)
    try:
        return ep.load()
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
            or _get_from_object_reference_str(scheme_value, entrypoint),
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
    version: version.ScmVersion,
    entrypoint: str,
    given_value: _t.VERSION_SCHEMES,
    default: str,
) -> str: ...


@overload
def _call_version_scheme(
    version: version.ScmVersion,
    entrypoint: str,
    given_value: _t.VERSION_SCHEMES,
    default: None,
) -> str | None: ...


def _call_version_scheme(
    version: version.ScmVersion,
    entrypoint: str,
    given_value: _t.VERSION_SCHEMES,
    default: str | None,
) -> str | None:
    for scheme in _iter_version_schemes(entrypoint, given_value):
        result = scheme(version)
        if result is not None:
            return result
    return default
