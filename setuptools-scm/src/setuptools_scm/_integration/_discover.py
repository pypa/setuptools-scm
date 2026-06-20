"""Setuptools-scm discovery factories for the vcs_versioning.discover_workdir group.

Provides egg-info based fallback discovery for setuptools builds.
"""

from __future__ import annotations

import logging

from pathlib import Path

log = logging.getLogger(__name__)


def discover_pkginfo(path: Path, *, config: object) -> object | None:
    """Probe *path* for ``PKG-INFO`` (a setuptools sdist artifact).

    Returns a ``PkgInfoWorkdir`` if found, ``None`` otherwise.
    """
    if (path / "PKG-INFO").is_file():
        from vcs_versioning._fallback_workdir import PkgInfoWorkdir

        return PkgInfoWorkdir(path=path)
    return None


def discover_egg_info_metadata(path: Path, *, config: object) -> object | None:
    """Probe *path* for ``*.egg-info/scm_version.json``.

    Returns a ``MetadataWorkdir`` reading version data + file list from
    egg-info, or ``None`` if no suitable egg-info directory is found.
    """
    from vcs_versioning._fallback_workdir import MetadataWorkdir
    from vcs_versioning._scm_metadata import SCM_VERSION_FILENAME

    for candidate in path.iterdir() if path.is_dir() else []:
        if candidate.is_dir() and candidate.name.endswith(".egg-info"):
            version_json = candidate / SCM_VERSION_FILENAME
            if version_json.is_file():
                log.debug("found egg-info metadata at %s", candidate)
                return MetadataWorkdir(path=path, metadata_dir=candidate)
    return None
