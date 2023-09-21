from __future__ import annotations

import sys
from typing import Any
from typing import Callable
from typing import cast
from typing import Iterator
from typing import overload
from typing import Protocol
from typing import TYPE_CHECKING

from . import _log
from . import version

if TYPE_CHECKING:
    from . import _types as _t
    from ._config import Configuration, ParseFunction


log = _log.log.getChild("entrypoints")


class EntrypointProtocol(Protocol):
    name: str
    value: str

    def load(self) -> Any:
        pass


def version_from_entrypoint(
    config: Configuration, entrypoint: str, root: _t.PathT
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


if sys.version_info[:2] < (3, 10):
    from importlib_metadata import entry_points
    from importlib_metadata import EntryPoint
else:
    from importlib.metadata import entry_points
    from importlib.metadata import EntryPoint


def iter_entry_points(
    group: str, name: str | None = None
) -> Iterator[EntrypointProtocol]:
    eps = entry_points(group=group)
    res = (
        eps
        if name is None
        else eps.select(  # type: ignore [no-untyped-call]
            name=name,
        )
    )

    return cast(Iterator[EntrypointProtocol], iter(res))


def _get_ep(group: str, name: str) -> Any | None:
    for ep in iter_entry_points(group, name):
        log.debug("ep found: %s", ep.name)
        return ep.load()
    else:
        return None


def _get_from_object_reference_str(path: str, group: str) -> Any | None:
    # todo: remove for importlib native spelling
    ep: EntrypointProtocol = EntryPoint(path, path, group)
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
) -> str:
    ...


@overload
def _call_version_scheme(
    version: version.ScmVersion,
    entrypoint: str,
    given_value: _t.VERSION_SCHEMES,
    default: None,
) -> str | None:
    ...


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
