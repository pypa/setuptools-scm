import os
import warnings

import setuptools

from . import _get_version
from . import _version_missing
from .config import _read_dist_name_from_setup_cfg
from .config import Configuration
from .utils import do
from .utils import iter_entry_points
from .utils import trace


def _warn_on_old_setuptools(_version=setuptools.__version__):
    if int(_version.split(".")[0]) < 45:
        warnings.warn(
            RuntimeWarning(
                f"""
ERROR: setuptools=={_version} is used in combination with setuptools_scm>=6.x

Your build configuration is incomplete and previously worked by accident!


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


def _assign_version(dist: setuptools.Distribution, config: Configuration):
    maybe_version = _get_version(config)

    if maybe_version is None:
        _version_missing(config)
    else:
        dist.metadata.version = maybe_version


def version_keyword(dist: setuptools.Distribution, keyword, value):
    if not value:
        return
    if value is True:
        value = {}
    if getattr(value, "__call__", None):
        value = value()
    assert (
        "dist_name" not in value
    ), "dist_name may not be specified in the setup keyword "

    trace(
        "version keyword",
        vars(dist.metadata),
    )
    dist_name = dist.metadata.name  # type: str | None
    if dist_name is None:
        dist_name = _read_dist_name_from_setup_cfg()
    config = Configuration(dist_name=dist_name, **value)
    _assign_version(dist, config)


def find_files(path=""):
    for ep in iter_entry_points("setuptools_scm.files_command"):
        command = ep.load()
        if isinstance(command, str):
            # this technique is deprecated
            res = do(ep.load(), path or ".").splitlines()
        else:
            res = command(path)
        if res:
            return res
    return []


def infer_version(dist: setuptools.Distribution):
    trace(
        "finalize hook",
        vars(dist.metadata),
    )
    dist_name = dist.metadata.name
    if not os.path.isfile("pyproject.toml"):
        return
    try:
        config = Configuration.from_file(dist_name=dist_name)
    except LookupError as e:
        trace(e)
    else:
        _assign_version(dist, config)
