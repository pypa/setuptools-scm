"""Egg-info mixin for workdir-based file finding and SCM metadata writing.

Overrides ``find_sources()`` so that when a workdir is available on the
Distribution (via ``VersionInferenceData``), the file list comes from
``workdir.list_tracked_files()`` instead of ``walk_revctrl()`` (which
dispatches to ``setuptools.file_finders`` entry points with no context).

Also writes ``scm_version.json`` and ``scm_file_list.json`` into the
egg-info directory after ``run()`` creates it, so that sdists carry
the metadata needed for fallback discovery when no VCS is present.
"""

from __future__ import annotations

import logging
import os

from pathlib import Path
from typing import TYPE_CHECKING

from setuptools.command.egg_info import egg_info as _egg_info
from setuptools.command.egg_info import manifest_maker
from setuptools.command.sdist import sdist
from setuptools.command.sdist import walk_revctrl

from .build_py import get_version_inference_data

if TYPE_CHECKING:
    from .build_py import VersionInferenceData

log = logging.getLogger(__name__)


class _ScmManifestMaker(manifest_maker):
    """``manifest_maker`` that uses pre-computed tracked files instead of
    ``walk_revctrl()``.

    Set ``_tracked_files`` before calling ``run()``; when ``None`` the
    standard ``walk_revctrl()`` path is used as fallback.
    """

    _tracked_files: list[str] | None = None

    def add_defaults(self) -> None:
        sdist.add_defaults(self)
        self.filelist.append(self.template)
        self.filelist.append(self.manifest)

        if self._tracked_files is not None:
            self.filelist.extend(self._tracked_files)
        else:
            rcfiles = list(walk_revctrl())
            if rcfiles:
                self.filelist.extend(rcfiles)
            elif os.path.exists(self.manifest):
                self.read_manifest()

        if os.path.exists("setup.py"):
            self.filelist.append("setup.py")

        ei_cmd = self.get_finalized_command("egg_info")
        self.filelist.graft(ei_cmd.egg_info)  # type: ignore[attr-defined,no-untyped-call]


def _normalize_tracked_files(files: list[str]) -> list[str]:
    """Convert absolute paths to CWD-relative paths for portable metadata."""
    cwd = os.getcwd()
    return [os.path.relpath(f, cwd) if os.path.isabs(f) else f for f in files]


def _get_tracked_files(data: VersionInferenceData | None) -> list[str] | None:
    """Extract tracked files from the workdir, or ``None`` to fall back.

    Paths are converted to be relative to the current working directory
    because setuptools' filelist rejects absolute paths.
    """
    if data is None or data.workdir is None:
        return None
    try:
        files = data.workdir.list_tracked_files()
        if files:
            return _normalize_tracked_files(files)
    except NotImplementedError:
        log.debug("workdir does not support list_tracked_files, using walk_revctrl")
    return None


class ScmEggInfoMixin(_egg_info):
    """Mixin for the ``egg_info`` command.

    * ``find_sources()`` -- uses the workdir from ``VersionInferenceData``
      to supply tracked files to ``manifest_maker`` without going through
      the ``setuptools.file_finders`` entry-point chain.
    * ``run()`` -- after the egg-info directory is created, writes
      ``scm_version.json`` and ``scm_file_list.json`` so that sdists
      carry fallback metadata.
    """

    def find_sources(self) -> None:
        data = get_version_inference_data(self.distribution)
        tracked = _get_tracked_files(data)

        if tracked is not None:
            manifest_filename = os.path.join(self.egg_info, "SOURCES.txt")
            mm = _ScmManifestMaker(self.distribution)
            mm.ignore_egg_info_dir = self.ignore_egg_info_in_manifest  # type: ignore[attr-defined]
            mm.manifest = manifest_filename
            mm._tracked_files = tracked
            mm.run()
            self.filelist = mm.filelist
        else:
            super().find_sources()

    def run(self) -> None:
        super().run()
        self._write_scm_metadata()

    def _write_scm_metadata(self) -> None:
        """Write ``scm_version.json`` and ``scm_file_list.json`` into egg-info."""
        data = get_version_inference_data(self.distribution)
        if data is None:
            return
        scm_version = data.scm_version
        if scm_version is None or scm_version.preformatted:
            return

        try:
            from vcs_versioning._scm_metadata import scm_version_data_from_scm_version
            from vcs_versioning._scm_metadata import write_scm_file_list
            from vcs_versioning._scm_metadata import write_scm_version_data

            egg_info_dir = Path(self.egg_info)
            if not egg_info_dir.is_dir():
                return

            version_data = scm_version_data_from_scm_version(scm_version)
            write_scm_version_data(egg_info_dir, version_data)

            if data.workdir is not None:
                try:
                    files = data.workdir.list_tracked_files()
                    if files:
                        write_scm_file_list(
                            egg_info_dir, _normalize_tracked_files(files)
                        )
                except NotImplementedError:
                    log.debug("workdir does not support list_tracked_files")

        except Exception:
            log.debug("failed to write SCM metadata to egg-info", exc_info=True)


class egg_info(ScmEggInfoMixin, _egg_info):
    """Default egg_info with SCM file finding and metadata writing."""
