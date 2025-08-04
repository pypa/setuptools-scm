from __future__ import annotations

import logging
import os
import warnings

from typing import Any
from typing import Callable

import setuptools

from .. import _config

log = logging.getLogger(__name__)


def read_dist_name_from_setup_cfg(
    input: str | os.PathLike[str] = "setup.cfg",
) -> str | None:
    # minimal effort to read dist_name off setup.cfg metadata
    import configparser

    parser = configparser.ConfigParser()
    parser.read([input], encoding="utf-8")
    dist_name = parser.get("metadata", "name", fallback=None)
    return dist_name


def _warn_on_old_setuptools(_version: str = setuptools.__version__) -> None:
    if int(_version.split(".")[0]) < 61:
        warnings.warn(
            RuntimeWarning(
                f"""
ERROR: setuptools=={_version} is used in combination with setuptools-scm>=8.x

Your build configuration is incomplete and previously worked by accident!
setuptools-scm requires setuptools>=61 (recommended: >=80)

Suggested workaround if applicable:
 - migrating from the deprecated setup_requires mechanism to pep517/518
   and using a pyproject.toml to declare build dependencies
   which are reliably pre-installed before running the build tools
"""
            )
        )


def _extract_package_name(requirement: str) -> str:
    """Extract the package name from a requirement string.

    Examples:
        'setuptools_scm' -> 'setuptools_scm'
        'setuptools-scm>=8' -> 'setuptools-scm'
        'setuptools_scm[toml]>=7.0' -> 'setuptools_scm'
    """
    # Split on common requirement operators and take the first part
    # This handles: >=, <=, ==, !=, >, <, ~=
    import re

    # Remove extras like [toml] first
    requirement = re.sub(r"\[.*?\]", "", requirement)
    # Split on version operators
    package_name = re.split(r"[><=!~]", requirement)[0].strip()
    return package_name


def _assign_version(
    dist: setuptools.Distribution, config: _config.Configuration
) -> None:
    from .._get_version_impl import _get_version
    from .._get_version_impl import _version_missing

    # todo: build time plugin
    maybe_version = _get_version(config, force_write_version_files=True)

    if maybe_version is None:
        _version_missing(config)
    else:
        assert dist.metadata.version is None
        dist.metadata.version = maybe_version


_warn_on_old_setuptools()


def _log_hookstart(hook: str, dist: setuptools.Distribution) -> None:
    log.debug("%s %r", hook, vars(dist.metadata))


def version_keyword(
    dist: setuptools.Distribution,
    keyword: str,
    value: bool | dict[str, Any] | Callable[[], dict[str, Any]],
) -> None:
    overrides: dict[str, Any]
    if value is True:
        overrides = {}
    elif callable(value):
        overrides = value()
    else:
        assert isinstance(value, dict), "version_keyword expects a dict or True"
        overrides = value

    assert "dist_name" not in overrides, (
        "dist_name may not be specified in the setup keyword "
    )
    dist_name: str | None = dist.metadata.name
    _log_hookstart("version_keyword", dist)

    if dist.metadata.version is not None:
        # Check if version was set by infer_version
        was_set_by_infer = getattr(dist, "_setuptools_scm_version_set_by_infer", False)

        if was_set_by_infer:
            # Version was set by infer_version, check if we have overrides
            if not overrides:
                # No overrides, just use the infer_version result
                return
            # We have overrides, clear the marker and proceed to override the version
            dist._setuptools_scm_version_set_by_infer = False  # type: ignore[attr-defined]
            dist.metadata.version = None
        else:
            # Version was set by something else, warn and return
            warnings.warn(f"version of {dist_name} already set")
            return

    if dist_name is None:
        dist_name = read_dist_name_from_setup_cfg()

    config = _config.Configuration.from_file(
        dist_name=dist_name,
        missing_file_ok=True,
        **overrides,
    )
    _assign_version(dist, config)


def infer_version(dist: setuptools.Distribution) -> None:
    _log_hookstart("infer_version", dist)
    log.debug("dist %s %s", id(dist), id(dist.metadata))
    if dist.metadata.version is not None:
        return  # metadata already added by hook
    dist_name = dist.metadata.name
    if dist_name is None:
        dist_name = read_dist_name_from_setup_cfg()
    if not os.path.isfile("pyproject.toml"):
        return
    if dist_name == "setuptools-scm":
        return

    try:
        config = _config.Configuration.from_file(dist_name=dist_name)
    except LookupError as e:
        log.info(e, exc_info=True)
    else:
        _assign_version(dist, config)
        # Mark that this version was set by infer_version
        dist._setuptools_scm_version_set_by_infer = True  # type: ignore[attr-defined]
