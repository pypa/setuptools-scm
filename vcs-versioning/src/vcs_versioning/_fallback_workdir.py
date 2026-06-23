"""Fallback workdir implementations for non-VCS contexts.

A FallbackWorkdir exists only at the project directory -- no surrounding
VCS checkout.  Version comes from static files; file lists come from
exported metadata.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from dataclasses import field as dc_field
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from ._integration import data_from_mime
from ._scm_metadata import read_scm_file_list, read_scm_version_data
from ._scm_version import ScmVersion, meta, tag_to_version

if TYPE_CHECKING:
    from ._config import Configuration

log = logging.getLogger(__name__)


@dataclass()
class FallbackWorkdir:
    """Base for work directories without a live VCS checkout."""

    path: Path

    _config: Configuration | None = dc_field(default=None, repr=False, compare=False)
    """Back-reference to the ``Configuration`` that discovered this workdir."""

    @property
    def project_root(self) -> Path:
        """Fallback workdirs always live at the project root."""
        return self.path

    @property
    def config(self) -> Configuration:
        if self._config is None:
            raise RuntimeError(
                f"{type(self).__name__} has no associated Configuration. "
                "Use Configuration.discover_workdir() to obtain a properly "
                "configured workdir, or set workdir._config = config explicitly."
            )
        return self._config

    def get_scm_version(self) -> ScmVersion | None:
        raise NotImplementedError

    def list_tracked_files(self, path: Path | str = "") -> list[str]:
        raise NotImplementedError


@dataclass()
class MetadataWorkdir(FallbackWorkdir):
    """Reads ``scm_version.json`` / ``scm_file_list.json`` written by a build backend."""

    metadata_dir: Path | None = dc_field(default=None)

    def __post_init__(self) -> None:
        if self.metadata_dir is None:
            self.metadata_dir = self.path

    def get_scm_version(self) -> ScmVersion | None:
        assert self.metadata_dir is not None
        data = read_scm_version_data(self.metadata_dir)
        if data is None:
            return None
        node_date: date | None = None
        if data.node_date:
            try:
                node_date = date.fromisoformat(data.node_date)
            except ValueError:
                log.warning(
                    "invalid node_date %r in metadata at %s, ignoring",
                    data.node_date,
                    self.metadata_dir,
                )
        # The tag in scm_version.json is already a parsed version string
        # (e.g. "1.5.5"), not a raw VCS tag (e.g. "cuda-pathfinder-v1.5.5").
        # Convert to version_cls so _parse_tag skips tag_regex matching.
        try:
            tag = self.config.version_cls(data.tag)
        except Exception:
            log.warning(
                "cannot parse stored tag %r in metadata at %s",
                data.tag,
                self.metadata_dir,
            )
            return None
        return meta(
            tag=tag,
            distance=data.distance,
            node=data.node,
            dirty=data.dirty,
            branch=data.branch,
            config=self.config,
            node_date=node_date,
        )

    def list_tracked_files(self, path: Path | str = "") -> list[str]:
        assert self.metadata_dir is not None
        files = read_scm_file_list(self.metadata_dir)
        return files if files is not None else []


@dataclass()
class ArchivedWorkdir(FallbackWorkdir):
    """Reads ``.git_archival.txt`` or ``.hg_archival.txt``."""

    archival_path: Path | None = dc_field(default=None)

    def __post_init__(self) -> None:
        if self.archival_path is None:
            self.archival_path = self.path

    def get_scm_version(self) -> ScmVersion | None:
        assert self.archival_path is not None
        for name, parser in [
            (".git_archival.txt", _parse_git_archival),
            (".hg_archival.txt", _parse_hg_archival),
        ]:
            archival = self.archival_path / name
            if archival.is_file():
                data = data_from_mime(archival)
                return parser(data, self.config)
        return None

    def list_tracked_files(self, path: Path | str = "") -> list[str]:
        files = read_scm_file_list(self.path)
        if files is not None:
            return files
        from ._file_finders import scm_find_files

        return scm_find_files(
            str(path) if path else str(self.path), set(), set(), force_all_files=True
        )


@dataclass()
class PkgInfoWorkdir(FallbackWorkdir):
    """Reads ``PKG-INFO`` for version; file list from ``scm_file_list.json`` if present."""

    def get_scm_version(self) -> ScmVersion | None:
        pkginfo = self.path / "PKG-INFO"
        if not pkginfo.is_file():
            return None
        data = data_from_mime(pkginfo)
        version_str = data.get("Version", "UNKNOWN")
        if version_str == "UNKNOWN":
            return None
        return meta(version_str, preformatted=True, config=self.config)

    def list_tracked_files(self, path: Path | str = "") -> list[str]:
        files = read_scm_file_list(self.path)
        return files if files is not None else []


@dataclass()
class StaticWorkdir(FallbackWorkdir):
    """Uses ``config.fallback_version`` / ``parentdir_prefix_version``; no file list."""

    def get_scm_version(self) -> ScmVersion | None:
        config = self.config
        if config.parentdir_prefix_version is not None:
            _, parent_name = os.path.split(os.path.abspath(self.path))
            if parent_name.startswith(config.parentdir_prefix_version):
                version = tag_to_version(
                    parent_name[len(config.parentdir_prefix_version) :], config
                )
                if version is not None:
                    return meta(str(version), preformatted=True, config=config)
        if config.fallback_version is not None:
            log.debug("FALLBACK %s", config.fallback_version)
            return meta(config.fallback_version, preformatted=True, config=config)
        return None

    def list_tracked_files(self, path: Path | str = "") -> list[str]:
        return []


# ------------------------------------------------------------------
# Discovery factories for fallback workdirs
# ------------------------------------------------------------------


def discover_archival(path: Path, *, config: Configuration) -> FallbackWorkdir | None:
    """Probe *path* for ``.git_archival.txt`` or ``.hg_archival.txt``."""
    for name in (".git_archival.txt", ".hg_archival.txt"):
        if (path / name).is_file():
            return ArchivedWorkdir(path=path, archival_path=path)
    return None


# ------------------------------------------------------------------
# Archival parsers (thin wrappers around existing logic)
# ------------------------------------------------------------------


def _parse_git_archival(
    data: dict[str, str], config: Configuration
) -> ScmVersion | None:
    from ._backends._git import archival_to_version

    return archival_to_version(data, config)


def _parse_hg_archival(
    data: dict[str, str], config: Configuration
) -> ScmVersion | None:
    from ._backends._hg import archival_to_version

    return archival_to_version(data, config)
