"""Setuptools-scm discovery factories for the vcs_versioning.discover_workdir group.

Provides egg-info based fallback discovery for setuptools builds.

``PKG-INFO`` discovery moved to :mod:`vcs_versioning._fallback_workdir` --
it is standard sdist metadata, not a setuptools artifact (:issue:`1507`).
``discover_pkginfo`` stays re-exported here so entry points recorded by an
older install keep resolving.
"""

from __future__ import annotations

import logging

from pathlib import Path

from vcs_versioning._config import Configuration
from vcs_versioning._fallback_workdir import MetadataWorkdir
from vcs_versioning._fallback_workdir import discover_pkginfo as discover_pkginfo
from vcs_versioning._scm_metadata import SCM_VERSION_FILENAME

log = logging.getLogger(__name__)


def discover_egg_info_metadata(
    path: Path, *, config: Configuration
) -> MetadataWorkdir | None:
    """Probe *path* for ``*.egg-info/scm_version.json``.

    Returns a ``MetadataWorkdir`` reading version data + file list from
    egg-info, or ``None`` if no suitable egg-info directory is found.
    """
    for candidate in path.iterdir() if path.is_dir() else []:
        if candidate.is_dir() and candidate.name.endswith(".egg-info"):
            version_json = candidate / SCM_VERSION_FILENAME
            if version_json.is_file():
                log.debug("found egg-info metadata at %s", candidate)
                return MetadataWorkdir(path=path, metadata_dir=candidate)
    return None
