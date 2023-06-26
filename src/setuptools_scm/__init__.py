"""
:copyright: 2010-2023 by Ronny Pfannschmidt
:license: MIT
"""
from __future__ import annotations

from typing import Any
from typing import Pattern

from . import _config
from . import _types as _t
from ._config import Configuration
from ._version_cls import NonNormalizedVersion
from ._version_cls import Version
from .version import ScmVersion


def dump_version(
    root: _t.PathT,
    version: str,
    write_to: _t.PathT,
    template: str | None = None,
    scm_version: ScmVersion | None = None,
) -> None:
    from ._integration.dump_version import dump_version as real

    return real(root, version, write_to, template, scm_version)


def get_version(
    root: _t.PathT = ".",
    version_scheme: _t.VERSION_SCHEME = _config.DEFAULT_VERSION_SCHEME,
    local_scheme: _t.VERSION_SCHEME = _config.DEFAULT_LOCAL_SCHEME,
    write_to: _t.PathT | None = None,
    write_to_template: str | None = None,
    relative_to: _t.PathT | None = None,
    tag_regex: str | Pattern[str] = _config.DEFAULT_TAG_REGEX,
    parentdir_prefix_version: str | None = None,
    fallback_version: str | None = None,
    fallback_root: _t.PathT = ".",
    parse: Any | None = None,
    git_describe_command: _t.CMD_TYPE | None = None,
    dist_name: str | None = None,
    version_cls: Any | None = None,
    normalize: bool = True,
    search_parent_directories: bool = False,
) -> str:
    params = {**locals()}
    from ._get_version import get_version

    return get_version(**locals())


# Public API
__all__ = [
    "get_version",
    "dump_version",
    "Configuration",
    "Version",
    "NonNormalizedVersion",
]
