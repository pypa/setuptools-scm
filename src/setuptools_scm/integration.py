from . import _get_version
from . import Configuration
from ._trace import trace
from ._trace import trace_exception
from .utils import do
from .utils import iter_entry_points


def version_keyword(dist, keyword, value):
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


def _args_from_toml(name="pyproject.toml"):
    # todo: more sensible config initialization
    # move this helper back to config and unify it with the code from get_config
    import tomli

    with open(name, encoding="UTF-8") as strm:
        defn = tomli.load(strm)
    return defn.get("tool", {})["setuptools_scm"]


def infer_version(dist):
    trace(
        "finalize hook",
        vars(dist.metadata),
    )
    dist_name = dist.metadata.name
    try:
        config = Configuration.from_file(dist_name=dist_name)
    except Exception:
        return trace_exception()
    dist.metadata.version = _get_version(config)
