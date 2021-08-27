import warnings

import setuptools

from . import _get_version
from . import Configuration
from .utils import do
from .utils import iter_entry_points
from .utils import trace


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
