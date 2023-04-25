from __future__ import annotations

import warnings
from typing import Any
from typing import Callable
from typing import cast
from typing import Iterator
from typing import overload
from typing import TYPE_CHECKING

from . import version
from ._trace import trace

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
    from importlib.metadata import EntryPoint
except ImportError:
    try:
        from importlib_metadata import entry_points
        from importlib_metadata import EntryPoint
    except ImportError:
        from collections import defaultdict

        def entry_points() -> dict[str, list[_t.EntrypointProtocol]]:
            warnings.warn(
                "importlib metadata missing, "
                "this may happen at build time for python3.7"
            )
            return defaultdict(list)

        class EntryPoint:  # type: ignore
            def __init__(self, *args: Any, **kwargs: Any):
                pass  # entry_points() already provides the warning


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


def _get_from_object_reference_str(path: str, absolute_root) -> Any | None:
    try:
        return EntryPoint(path, path, None).load()
    except ModuleNotFoundError:
        try:
            import os
            from importlib.util import spec_from_file_location, module_from_spec

            filename, func = path.rsplit(":", 1)
            spec = spec_from_file_location(
                func, os.path.join(absolute_root, filename + ".py")
            )
            module = module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, func)
        except (ValueError, ModuleNotFoundError, AttributeError):
            return None
    except AttributeError:
        return None


def _iter_version_schemes(
    entrypoint: str,
    scheme_value: _t.VERSION_SCHEMES,
    absolute_root: str,
    _memo: set[object] | None = None,
) -> Iterator[Callable[[version.ScmVersion], str]]:
    if _memo is None:
        _memo = set()
    if isinstance(scheme_value, str):
        scheme_value = cast(
            "_t.VERSION_SCHEMES",
            _get_ep(entrypoint, scheme_value)
            or _get_from_object_reference_str(scheme_value, absolute_root),
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
    version: version.ScmVersion,
    entypoint: str,
    given_value: str,
    absolute_root: str,
    default: str | None,
) -> str | None:
    for scheme in _iter_version_schemes(entypoint, given_value, absolute_root):
        result = scheme(version)
        if result is not None:
            return result
    return default
