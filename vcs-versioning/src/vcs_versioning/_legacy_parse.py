"""Legacy parse entry-point dispatch.

These helpers invoke the old ``setuptools_scm.parse_scm`` /
``setuptools_scm.parse_scm_fallback`` entry-point groups.  They exist
only to support third-party plugins that have not yet migrated to the
``vcs_versioning.discover_workdir`` entry-point group.
"""

from __future__ import annotations

import logging
from pathlib import Path

from . import _entrypoints, _run_cmd
from ._config import Configuration
from ._scm_version import ScmVersion

log = logging.getLogger(__name__)


def resolved_fallback_root(config: Configuration) -> str:
    """Absolute path for *fallback_root* when it is relative to *relative_to*'s directory."""
    rel = config.relative_to
    if rel and not Path(config.fallback_root).is_absolute():
        return str((Path(rel).resolve().parent / config.fallback_root).resolve())
    return str(Path(config.fallback_root).resolve())


def parse_scm_version(config: Configuration) -> ScmVersion | None:
    """Dispatch to ``setuptools_scm.parse_scm`` entry points."""
    try:
        return _entrypoints.version_from_entrypoint(
            config,
            entrypoint="setuptools_scm.parse_scm",
            root=config.absolute_root,
        )
    except _run_cmd.CommandNotFoundError as e:
        log.exception("command %s not found while parsing the scm, using fallbacks", e)
        return None


def parse_fallback_version(config: Configuration) -> ScmVersion | None:
    """Dispatch to ``setuptools_scm.parse_scm_fallback`` entry points."""
    return _entrypoints.version_from_entrypoint(
        config,
        entrypoint="setuptools_scm.parse_scm_fallback",
        root=resolved_fallback_root(config),
    )


def has_legacy_parse_eps() -> bool:
    """True when third-party plugins still register old parse EP groups."""
    from ._entrypoints import entry_points as _eps

    for group in ("setuptools_scm.parse_scm", "setuptools_scm.parse_scm_fallback"):
        for ep in _eps(group=group):
            if not ep.value.startswith("vcs_versioning."):
                return True
    return False
