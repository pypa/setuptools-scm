from __future__ import annotations

import os
from typing import Any

from . import _config
from . import _log
from . import version
from ._integration.pyproject_reading import lazy_toml_load

log = _log.log.getChild("overrides")

PRETEND_KEY = "SETUPTOOLS_SCM_PRETEND_VERSION"
PRETEND_KEY_NAMED = PRETEND_KEY + "_FOR_{name}"


def read_named_env(
    *, tool: str = "SETUPTOOLS_SCM", name: str, dist_name: str | None
) -> str | None:
    if dist_name is not None:
        val = os.environ.get(f"{tool}_{name}_FOR_{dist_name.upper()}")
        if val is not None:
            return val
    return os.environ.get(f"{tool}_{name}")


def _read_pretended_version_for(
    config: _config.Configuration,
) -> version.ScmVersion | None:
    """read a a overridden version from the environment

    tries ``SETUPTOOLS_SCM_PRETEND_VERSION``
    and ``SETUPTOOLS_SCM_PRETEND_VERSION_FOR_$UPPERCASE_DIST_NAME``
    """
    log.debug("dist name: %s", config.dist_name)

    pretended = read_named_env(name="PRETEND_VERSION", dist_name=config.dist_name)

    if pretended:
        # we use meta here since the pretended version
        # must adhere to the pep to begin with
        return version.meta(tag=pretended, preformatted=True, config=config)
    else:
        return None


def read_toml_overrides(dist_name: str | None) -> dict[str, Any]:
    data = read_named_env(name="OVERRIDES", dist_name=dist_name)
    if data:
        if data[0] == "{":
            data = "cheat=" + data
            loaded = lazy_toml_load(data)
            return loaded["cheat"]  # type: ignore[no-any-return]
        return lazy_toml_load(data)
    else:
        return {}
