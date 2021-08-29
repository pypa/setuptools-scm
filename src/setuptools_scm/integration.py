import warnings

import setuptools

from . import _get_version
from . import Configuration
from .utils import do
from .utils import iter_entry_points
from .utils import trace


def _break_on_old_setuptools(_version=setuptools.__version__):
    if int(_version.split(".")[0]) < 45:
        raise SystemExit(
            f"""
ERROR: setuptools=={_version} is used in combination with setuptools_scm>=6.x

Your build configuration is incomplete and worked by accident!
Please ensure setuptools>=45 and setuptools_scm>=6.2 are installed with current tools.

This happens as setuptools is unable to replace itself when a activated build dependeny
requires a more recent setuptools version.

Suggested workarounds if applicable:
 - preinstalling build dependencies like setuptools_scm before running setup.py
 - installing setuptools_scm using the system package manager to ensure consistency
 - migrating from the deprecated setup_requires mechanism to pep517/518
   and using a pyproject.toml to declare build dependencies
   which are reliably pre-installed before running the build tools
"""
        )


_break_on_old_setuptools()


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
    dist_name = dist.metadata.name
    config = Configuration(dist_name=dist_name, **value)
    dist.metadata.version = _get_version(config)


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
    try:
        config = Configuration.from_file(dist_name=dist_name)
    except FileNotFoundError as e:
        warnings.warn(str(e))
    else:
        dist.metadata.version = _get_version(config)
