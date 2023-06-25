"""
:copyright: 2010-2023 by Ronny Pfannschmidt
:license: MIT
"""
from __future__ import annotations

import re
import warnings
from typing import Any
from typing import Pattern
from typing import TYPE_CHECKING

from . import _config
from ._config import Configuration
from ._entrypoints import _version_from_entrypoints
from ._overrides import _read_pretended_version_for
from ._version_cls import _validate_version_cls
from ._version_cls import NonNormalizedVersion
from ._version_cls import Version
from .version import format_version as _format_version
from .version import ScmVersion

if TYPE_CHECKING:
    from typing import NoReturn
    from . import _types as _t


def dump_version(
    root: _t.PathT,
    version: str,
    write_to: _t.PathT,
    template: str | None = None,
    scm_version: ScmVersion | None = None,
) -> None:
    from ._integration.dump_version import dump_version as real

    return real(root, version, write_to, template, scm_version)


def _do_parse(config: Configuration) -> _t.SCMVERSION | None:
    from .version import ScmVersion

    pretended = _read_pretended_version_for(config)
    if pretended is not None:
        return pretended
    parsed_version: ScmVersion | None
    if config.parse:
        parse_result = config.parse(config.absolute_root, config=config)
        if isinstance(parse_result, str):
            raise TypeError(
                f"version parse result was {str!r}\nplease return a parsed version"
            )

        if parse_result:
            assert isinstance(parse_result, ScmVersion)
            parsed_version = parse_result
        else:
            parsed_version = _version_from_entrypoints(config, fallback=True)
    else:
        # include fallbacks after dropping them from the main entrypoint
        parsed_version = _version_from_entrypoints(config) or _version_from_entrypoints(
            config, fallback=True
        )

    return parsed_version


def _version_missing(config: Configuration) -> NoReturn:
    raise LookupError(
        f"setuptools-scm was unable to detect version for {config.absolute_root}.\n\n"
        "Make sure you're either building from a fully intact git repository "
        "or PyPI tarballs. Most other sources (such as GitHub's tarballs, a "
        "git checkout without the .git folder) don't contain the necessary "
        "metadata and will not work.\n\n"
        "For example, if you're using pip, instead of "
        "https://github.com/user/proj/archive/master.zip "
        "use git+https://github.com/user/proj.git#egg=proj"
    )


def get_version(
    root: _t.PathT = ".",
    version_scheme: _t.VERSION_SCHEME = _config.DEFAULT_VERSION_SCHEME,
    local_scheme: _t.VERSION_SCHEME = _config.DEFAULT_LOCAL_SCHEME,
    write_to: _t.PathT | None = None,
    write_to_template: str | None = None,
    relative_to: str | None = None,
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
    """
    If supplied, relative_to should be a file from which root may
    be resolved. Typically called by a script or module that is not
    in the root of the repository to direct setuptools_scm to the
    root of the repository by supplying ``__file__``.
    """
    version_cls = _validate_version_cls(version_cls, normalize)
    del normalize
    if isinstance(tag_regex, str):
        if tag_regex == "":
            warnings.warn(
                DeprecationWarning(
                    "empty regex for tag regex is invalid, using default"
                )
            )
            tag_regex = _config.DEFAULT_TAG_REGEX
        else:
            tag_regex = re.compile(tag_regex)
    config = Configuration(**locals())
    maybe_version = _get_version(config)

    if maybe_version is None:
        _version_missing(config)
    return maybe_version


def _get_version(config: Configuration) -> str | None:
    parsed_version = _do_parse(config)
    if parsed_version is None:
        return None
    version_string = _format_version(
        parsed_version,
        version_scheme=config.version_scheme,
        local_scheme=config.local_scheme,
    )
    if config.write_to is not None:
        dump_version(
            root=config.root,
            version=version_string,
            scm_version=parsed_version,
            write_to=config.write_to,
            template=config.write_to_template,
        )

    return version_string


# Public API
__all__ = [
    "get_version",
    "dump_version",
    "Configuration",
    "Version",
    "NonNormalizedVersion",
]
