"""setuptools-scm wrappers for vcs_versioning get_version APIs.

``get_version`` and ``_get_version`` enter :class:`~vcs_versioning.overrides.GlobalOverrides`
for the ``SETUPTOOLS_SCM`` tool prefix so callers (e.g. ``setup.py`` / library code) do not
trigger implicit context auto-creation warnings from vcs_versioning.
"""

from __future__ import annotations

import logging

from re import Pattern
from typing import Any

from vcs_versioning import _config
from vcs_versioning import _types as _t
from vcs_versioning._config import Configuration
from vcs_versioning._get_version_impl import _get_version as _get_version_core
from vcs_versioning._get_version_impl import get_version as _get_version_public
from vcs_versioning.overrides import ensure_context

_setuptools_scm_logger = logging.getLogger("setuptools_scm")


def _get_version(
    config: Configuration, force_write_version_files: bool | None = None
) -> str | None:
    with ensure_context("SETUPTOOLS_SCM", additional_loggers=_setuptools_scm_logger):
        return _get_version_core(
            config, force_write_version_files=force_write_version_files
        )


def get_version(
    root: _t.PathT = ".",
    version_scheme: _t.VERSION_SCHEME = _config.DEFAULT_VERSION_SCHEME,
    local_scheme: _t.VERSION_SCHEME = _config.DEFAULT_LOCAL_SCHEME,
    write_to: _t.PathT | None = None,
    write_to_template: str | None = None,
    version_file: _t.PathT | None = None,
    version_file_template: str | None = None,
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
    scm: dict[str, Any] | None = None,
) -> str:
    with ensure_context("SETUPTOOLS_SCM", additional_loggers=_setuptools_scm_logger):
        return _get_version_public(
            root=root,
            version_scheme=version_scheme,
            local_scheme=local_scheme,
            write_to=write_to,
            write_to_template=write_to_template,
            version_file=version_file,
            version_file_template=version_file_template,
            relative_to=relative_to,
            tag_regex=tag_regex,
            parentdir_prefix_version=parentdir_prefix_version,
            fallback_version=fallback_version,
            fallback_root=fallback_root,
            parse=parse,
            git_describe_command=git_describe_command,
            dist_name=dist_name,
            version_cls=version_cls,
            normalize=normalize,
            search_parent_directories=search_parent_directories,
            scm=scm,
        )
