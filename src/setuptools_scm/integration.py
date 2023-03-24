from __future__ import annotations

import logging
import os
import textwrap
import warnings
from pathlib import Path
from typing import Any
from typing import Callable
from typing import TYPE_CHECKING

import setuptools

from . import _get_version
from . import _types as _t
from . import _version_missing
from . import Configuration
from ._integration.setuptools import (
    read_dist_name_from_setup_cfg as _read_dist_name_from_setup_cfg,
)
from ._version_cls import _validate_version_cls

log = logging.getLogger(__name__)
if TYPE_CHECKING:
    pass


def _warn_on_old_setuptools(_version: str = setuptools.__version__) -> None:
    if int(_version.split(".")[0]) < 45:
        warnings.warn(
            RuntimeWarning(
                f"""
ERROR: setuptools=={_version} is used in combination with setuptools_scm>=6.x

Your build configuration is incomplete and previously worked by accident!
setuptools_scm requires setuptools>=45


This happens as setuptools is unable to replace itself when a activated build dependency
requires a more recent setuptools version
(it does not respect "setuptools>X" in setup_requires).


setuptools>=31 is required for setup.cfg metadata support
setuptools>=42 is required for pyproject.toml configuration support

Suggested workarounds if applicable:
 - preinstalling build dependencies like setuptools_scm before running setup.py
 - installing setuptools_scm using the system package manager to ensure consistency
 - migrating from the deprecated setup_requires mechanism to pep517/518
   and using a pyproject.toml to declare build dependencies
   which are reliably pre-installed before running the build tools
"""
            )
        )


_warn_on_old_setuptools()


def _assign_version(dist: setuptools.Distribution, config: Configuration) -> None:
    maybe_version = _get_version(config)

    if maybe_version is None:
        _version_missing(config)
    else:
        assert dist.metadata.version is None
        dist.metadata.version = maybe_version


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
        dist_name = _read_dist_name_from_setup_cfg()
    version_cls = value.pop("version_cls", None)
    normalize = value.pop("normalize", True)
    final_version = _validate_version_cls(version_cls, normalize)
    config = Configuration(dist_name=dist_name, version_cls=final_version, **value)
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
        dist_name = _read_dist_name_from_setup_cfg()
    if not os.path.isfile("pyproject.toml"):
        return
    if dist_name == "setuptools_scm":
        return
    try:
        config = Configuration.from_file(dist_name=dist_name)
    except LookupError as e:
        log.exception(e)
    else:
        _assign_version(dist, config)


def data_from_mime(path: _t.PathT) -> dict[str, str]:
    content = Path(path).read_text(encoding="utf-8")
    log.debug("mime %s content:\n%s", path, textwrap.indent(content, "    "))
    # the complex conditions come from reading pseudo-mime-messages
    data = dict(x.split(": ", 1) for x in content.splitlines() if ": " in x)

    log.debug("mime %s data:\n%s", path, data)
    return data
