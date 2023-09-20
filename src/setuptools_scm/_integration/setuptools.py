from __future__ import annotations

import logging
import os
import warnings
from typing import Any
from typing import Callable

import setuptools

from .. import _config
from .._version_cls import _validate_version_cls

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
ERROR: setuptools=={_version} is used in combination with setuptools_scm>=8.x

Your build configuration is incomplete and previously worked by accident!
setuptools_scm requires setuptools>=61

Suggested workaround if applicable:
 - migrating from the deprecated setup_requires mechanism to pep517/518
   and using a pyproject.toml to declare build dependencies
   which are reliably pre-installed before running the build tools
"""
            )
        )


def _assign_version(
    dist: setuptools.Distribution, config: _config.Configuration
) -> None:
    from .._get_version_impl import _get_version, _version_missing

    # todo: build time plugin
    maybe_version = _get_version(config, force_write_version_files=True)

    if maybe_version is None:
        _version_missing(config)
    else:
        assert dist.metadata.version is None
        dist.metadata.version = maybe_version


_warn_on_old_setuptools()


def version_keyword(
    dist: setuptools.Distribution,
    keyword: str,
    value: bool | dict[str, Any] | Callable[[], dict[str, Any]],
) -> None:
    if not value:
        return
    elif value is True:
        value = {}
    elif callable(value):
        value = value()
    assert (
        "dist_name" not in value
    ), "dist_name may not be specified in the setup keyword "
    dist_name: str | None = dist.metadata.name
    if dist.metadata.version is not None:
        warnings.warn(f"version of {dist_name} already set")
        return
    log.debug(
        "version keyword %r",
        vars(dist.metadata),
    )
    log.debug("dist %s %s", id(dist), id(dist.metadata))

    if dist_name is None:
        dist_name = read_dist_name_from_setup_cfg()
    version_cls = value.pop("version_cls", None)
    normalize = value.pop("normalize", True)
    tag_regex = _config._check_tag_regex(
        value.pop("tag_regex", _config.DEFAULT_TAG_REGEX)
    )
    final_version = _validate_version_cls(version_cls, normalize)

    config = _config.Configuration(
        dist_name=dist_name, version_cls=final_version, tag_regex=tag_regex, **value
    )
    _assign_version(dist, config)


def infer_version(dist: setuptools.Distribution) -> None:
    log.debug(
        "finalize hook %r",
        vars(dist.metadata),
    )
    log.debug("dist %s %s", id(dist), id(dist.metadata))
    if dist.metadata.version is not None:
        return  # metadata already added by hook
    dist_name = dist.metadata.name
    if dist_name is None:
        dist_name = read_dist_name_from_setup_cfg()
    if not os.path.isfile("pyproject.toml"):
        return
    if dist_name == "setuptools_scm":
        return
    try:
        config = _config.Configuration.from_file(dist_name=dist_name)
    except LookupError as e:
        log.exception(e)
    else:
        _assign_version(dist, config)
