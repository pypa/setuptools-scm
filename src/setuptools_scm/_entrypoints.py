import warnings
from typing import Optional

from .config import Configuration
from .discover import iter_matching_entrypoints
from .utils import function_has_arg
from .utils import trace
from setuptools_scm.version import ScmVersion


def _call_entrypoint_fn(root, config, fn):
    if function_has_arg(fn, "config"):
        return fn(root, config=config)
    else:
        warnings.warn(
            f"parse function {fn.__module__}.{fn.__name__}"
            " are required to provide a named argument"
            " 'config', setuptools_scm>=8.0 will remove support.",
            category=DeprecationWarning,
            stacklevel=2,
        )
        return fn(root)


def _version_from_entrypoints(
    config: Configuration, fallback: bool = False
) -> "ScmVersion|None":
    if fallback:
        entrypoint = "setuptools_scm.parse_scm_fallback"
        root = config.fallback_root
    else:
        entrypoint = "setuptools_scm.parse_scm"
        root = config.absolute_root

    trace("version_from_ep", entrypoint, root)
    for ep in iter_matching_entrypoints(root, entrypoint, config):
        version: Optional[ScmVersion] = _call_entrypoint_fn(root, config, ep.load())
        trace(ep, version)
        if version:
            return version
    return None


try:
    from importlib.metadata import entry_points  # type: ignore
except ImportError:
    from pkg_resources import iter_entry_points
else:

    def iter_entry_points(group: str, name: Optional[str] = None):
        all_eps = entry_points()
        if hasattr(all_eps, "select"):
            eps = all_eps.select(group=group)
        else:
            eps = all_eps[group]
        if name is None:
            return iter(eps)
        return (ep for ep in eps if ep.name == name)
