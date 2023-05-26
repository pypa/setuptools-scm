from __future__ import annotations

import sys
from typing import Any
from typing import Callable
from typing import cast
from typing import Iterator
from typing import overload
from typing import TYPE_CHECKING

if sys.version_info[:2] >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol

from . import _log
from . import version

if TYPE_CHECKING:
    from ._config import Configuration
    from . import _types as _t


log = _log.log.getChild("entrypoints")


class EntrypointProtocol(Protocol):
    name: str

    def load(self) -> Any:
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

    log.debug("version_from_ep %s in %s", entrypoint, root)
    for ep in iter_matching_entrypoints(root, entrypoint, config):
        fn = ep.load()
        maybe_version: version.ScmVersion | None = fn(root, config=config)
        log.debug("%s found %r", ep, maybe_version)
        if maybe_version is not None:
            return maybe_version
    return None


try:
    from importlib_metadata import entry_points
    from importlib_metadata import EntryPoint
except ImportError:
    from importlib.metadata import entry_points  # type: ignore [no-redef, import]
    from importlib.metadata import EntryPoint  # type: ignore [no-redef]


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
    version: version.ScmVersion, entrypoint: str, given_value: str, default: str
) -> str:
    ...


@overload
def _call_version_scheme(
    version: version.ScmVersion, entrypoint: str, given_value: str, default: None
) -> str | None:
    ...


def _call_version_scheme(
    version: version.ScmVersion, entrypoint: str, given_value: str, default: str | None
) -> str | None:
    for scheme in _iter_version_schemes(entrypoint, given_value):
        result = scheme(version)
        if result is not None:
            return result
    return default
