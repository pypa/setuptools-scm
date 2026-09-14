"""bdist_wheel mixin that keeps SCM egg-info JSON out of wheels.

``egg_info`` writes ``scm_version.json`` / ``scm_file_list.json`` for sdist
fallback discovery. setuptools' ``egg2dist`` copies unknown egg-info files
into ``.dist-info``, so wheels would otherwise ship them. Wheels already
have ``METADATA`` and ``RECORD``; strip our files after conversion.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from setuptools.command.bdist_wheel import bdist_wheel as _bdist_wheel
from vcs_versioning._scm_metadata import SCM_FILE_LIST_FILENAME
from vcs_versioning._scm_metadata import SCM_VERSION_FILENAME

if TYPE_CHECKING:
    # Typing-only base -- see ``ScmBdistWheelMixin`` for why the mixin has no
    # runtime base class.
    _MixinBase = _bdist_wheel
else:
    _MixinBase = object

_SCM_DIST_INFO_FILES = (SCM_VERSION_FILENAME, SCM_FILE_LIST_FILENAME)


def _unlink_scm_metadata(distinfo_path: Path) -> None:
    """Remove SCM metadata files from a ``.dist-info`` directory if present."""
    for name in _SCM_DIST_INFO_FILES:
        (distinfo_path / name).unlink(missing_ok=True)


class ScmBdistWheelMixin(_MixinBase):
    """Mixin that strips SCM egg-info JSON from ``.dist-info`` after egg2dist.

    No runtime base class: projects commonly register a ``bdist_wheel``
    derived from the standalone ``wheel`` package rather than from
    setuptools' vendored copy, and those two hierarchies are disjoint.
    Inheriting here would put setuptools' ``bdist_wheel`` ahead of the
    project's class in the wrapped MRO (#1529).
    """

    def egg2dist(self, egginfo_path: str, distinfo_path: str) -> None:
        super().egg2dist(egginfo_path, distinfo_path)
        _unlink_scm_metadata(Path(distinfo_path))


class bdist_wheel(ScmBdistWheelMixin, _bdist_wheel):
    """Default bdist_wheel that omits SCM metadata from wheels."""
