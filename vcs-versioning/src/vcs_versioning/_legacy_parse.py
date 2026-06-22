"""Legacy parse entry-point dispatch and ``config.parse`` workdir wrapper.

These helpers invoke the old ``setuptools_scm.parse_scm`` /
``setuptools_scm.parse_scm_fallback`` entry-point groups.  They exist
only to support third-party plugins that have not yet migrated to the
``vcs_versioning.discover_workdir`` entry-point group.

``LegacyParseWorkdir`` wraps a ``config.parse`` callable as a
``ScmWorkdir`` so that the discovery pipeline handles it uniformly.
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass
from dataclasses import field as dc_field
from pathlib import Path
from typing import TYPE_CHECKING

from . import _entrypoints, _run_cmd
from ._backends._scm_workdir import ScmWorkdir
from ._config import Configuration
from ._scm_version import ScmVersion

if TYPE_CHECKING:
    from ._config import ParseFunction

log = logging.getLogger(__name__)


@dataclass()
class LegacyParseWorkdir(ScmWorkdir):
    """Wraps a legacy ``config.parse`` callable as a workdir.

    Emits a deprecation warning when ``get_scm_version`` is called.
    Users should migrate to the ``vcs_versioning.discover_workdir``
    entry-point group.
    """

    _parse_fn: ParseFunction | None = dc_field(default=None, repr=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        if self._parse_fn is None:
            raise TypeError("LegacyParseWorkdir requires a _parse_fn")

    def get_scm_version(self) -> ScmVersion | None:
        warnings.warn(
            "config.parse is deprecated. Migrate to the "
            "vcs_versioning.discover_workdir entry-point group. "
            "See https://setuptools-scm.readthedocs.io/en/latest/extending/",
            DeprecationWarning,
            stacklevel=2,
        )
        assert self._parse_fn is not None
        result = self._parse_fn(self.config.absolute_root, config=self.config)
        if result is not None and not isinstance(result, ScmVersion):
            raise TypeError(
                f"version parse result was {result!r}\n"
                "please return a parsed version (ScmVersion)"
            )
        return result


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
