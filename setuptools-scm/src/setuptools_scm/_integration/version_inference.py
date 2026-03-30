from __future__ import annotations

import logging
import os

from dataclasses import dataclass
from typing import Any
from typing import Protocol
from typing import TypeAlias

from setuptools import Distribution
from vcs_versioning._pyproject_reading import PyProjectData

from .build_py import VersionInferenceData
from .build_py import set_version_inference_data
from .pyproject_reading import should_infer

log = logging.getLogger(__name__)

# Environment variable to control writing version files to the source tree
# at inference time. By default, version files ARE written to source.
# Set to "0"/"false"/"no" to disable (e.g., for read-only source trees).
WRITE_TO_SOURCE_ENV_VAR = "SETUPTOOLS_SCM_WRITE_TO_SOURCE"


def _should_write_to_source() -> bool:
    """Check if version files should be written to source at inference time.

    Returns True by default. Returns False only if SETUPTOOLS_SCM_WRITE_TO_SOURCE
    is explicitly set to a falsy value ("0", "false", "no").
    """
    value = os.environ.get(WRITE_TO_SOURCE_ENV_VAR, "").lower()
    return value not in ("0", "false", "no")


def infer_version_with_config(
    dist_name: str | None,
    pyproject_data: PyProjectData,
    overrides: dict[str, Any] | None = None,
) -> VersionInferenceData:
    """Infer version and return VersionInferenceData.

    Runs the version pipeline inline:
    ``Configuration -> discover_workdir -> get_scm_version -> format_version``

    The discovered workdir is stored in the returned data so that downstream
    consumers (egg_info mixin, file finders) can access it without a ContextVar.

    Set SETUPTOOLS_SCM_WRITE_TO_SOURCE=0 to disable writing to the source tree
    (e.g., for read-only source directories like Bazel builds).

    Returns:
        VersionInferenceData containing version, Configuration, ScmVersion, and workdir
    """
    from vcs_versioning._config import Configuration
    from vcs_versioning._get_version_impl import _version_missing
    from vcs_versioning._get_version_impl import write_version_files
    from vcs_versioning._legacy_parse import has_legacy_parse_eps
    from vcs_versioning._legacy_parse import parse_fallback_version
    from vcs_versioning._legacy_parse import parse_scm_version
    from vcs_versioning._overrides import _apply_metadata_overrides
    from vcs_versioning._overrides import _read_pretended_version_for
    from vcs_versioning._version_schemes import format_version
    from vcs_versioning._worktree_discovery import discover_workdir

    config = Configuration.from_file(
        dist_name=dist_name, pyproject_data=pyproject_data, **(overrides or {})
    )

    workdir = None
    scm_version: Any = None

    pretended = _read_pretended_version_for(config)
    if pretended is not None:
        scm_version = pretended
    else:
        workdir = discover_workdir(config)
        if workdir is not None:
            scm_version = workdir.get_scm_version(config)

        if scm_version is None and has_legacy_parse_eps():
            scm_version = parse_scm_version(config) or parse_fallback_version(config)

    if scm_version is None:
        _version_missing(config)

    scm_version = _apply_metadata_overrides(scm_version, config)
    assert scm_version is not None
    version_string = format_version(scm_version)

    if _should_write_to_source():
        try:
            write_version_files(config, version=version_string, scm_version=scm_version)
        except OSError as e:
            log.warning(
                "Could not write version file to source tree: %s. "
                "The file will still be written to the build directory during build.",
                e,
            )

    _write_scm_metadata_to_egg_info(config, scm_version, dist_name, workdir)

    return VersionInferenceData(
        version=version_string,
        config=config,
        scm_version=scm_version,
        workdir=workdir,
    )


def _write_scm_metadata_to_egg_info(
    config: Any,
    scm_version: Any,
    dist_name: str | None,
    workdir: Any,
) -> None:
    """Write scm_version.json and scm_file_list.json into the egg-info directory.

    These files allow a wheel built from an sdist to discover version metadata
    and tracked files without a live VCS checkout.
    """
    if scm_version is None or scm_version.preformatted:
        return

    try:
        from pathlib import Path

        from vcs_versioning._scm_metadata import scm_version_data_from_scm_version
        from vcs_versioning._scm_metadata import write_scm_file_list
        from vcs_versioning._scm_metadata import write_scm_version_data

        if dist_name is None:
            return

        egg_info_name = dist_name.replace("-", "_") + ".egg-info"
        project_root = Path(config.absolute_root)
        if config.relative_to is not None:
            rel = Path(str(config.relative_to))
            project_root = rel.parent if rel.is_file() else rel

        egg_info_dir = project_root / egg_info_name
        if not egg_info_dir.is_dir():
            log.debug(
                "egg-info directory %s not found, skipping metadata write", egg_info_dir
            )
            return

        version_data = scm_version_data_from_scm_version(scm_version)
        write_scm_version_data(egg_info_dir, version_data)

        if workdir is not None:
            try:
                files = workdir.list_tracked_files()
                if files:
                    write_scm_file_list(egg_info_dir, files)
            except NotImplementedError:
                log.debug("workdir does not support list_tracked_files")

    except Exception:
        log.debug("failed to write SCM metadata to egg-info", exc_info=True)


class VersionInferenceApplicable(Protocol):
    """A result object from version inference decision that can be applied to a dist."""

    def apply(self, dist: Distribution) -> None:  # pragma: no cover - structural type
        ...


class GetVersionInferenceConfig(Protocol):
    """Callable protocol for the decision function used by integration points."""

    def __call__(
        self,
        dist_name: str | None,
        current_version: str | None,
        pyproject_data: PyProjectData,
        overrides: dict[str, object] | None = None,
    ) -> VersionInferenceApplicable:  # pragma: no cover - structural type
        ...


@dataclass
class VersionInferenceConfig:
    """Configuration for version inference."""

    dist_name: str | None
    pyproject_data: PyProjectData | None
    overrides: dict[str, Any] | None

    def apply(self, dist: Distribution) -> None:
        """Apply version inference to the distribution.

        Version files are written to the source tree by default (unless
        SETUPTOOLS_SCM_WRITE_TO_SOURCE=0). The version inference data is also
        stored on the distribution for build_py to write to the build directory.
        """
        data = infer_version_with_config(
            self.dist_name,
            self.pyproject_data,  # type: ignore[arg-type]
            self.overrides,
        )
        dist.metadata.version = data.version

        # Store version inference data for build_py to write to build directory
        set_version_inference_data(dist, data)
        log.debug(
            "Stored version inference data for build_py: version=%s", data.version
        )

        # Mark that this version was set by infer_version if overrides is None (infer_version context)
        if self.overrides is None:
            dist._setuptools_scm_version_set_by_infer = True  # type: ignore[attr-defined]


@dataclass
class VersionAlreadySetWarning:
    """Warning that version was already set, inference would override it."""

    dist_name: str | None

    def apply(self, dist: Distribution) -> None:
        """Warn user that version is already set."""
        import warnings

        warnings.warn(f"version of {self.dist_name} already set")


@dataclass(frozen=True)
class VersionInferenceNoOp:
    """No operation result - silent skip."""

    def apply(self, dist: Distribution) -> None:
        """Apply no-op to the distribution."""


VersionInferenceResult: TypeAlias = (
    VersionInferenceConfig  # Proceed with inference
    | VersionAlreadySetWarning  # Warn: version already set
    | VersionInferenceNoOp  # Don't infer (silent)
)


def infer_version_string(
    dist_name: str | None,
    pyproject_data: PyProjectData,
    overrides: dict[str, Any] | None = None,
    *,
    force_write_version_files: bool = False,
) -> str:
    """
    Compute the inferred version string from the given inputs without requiring a
    setuptools Distribution instance. This is a pure helper that simplifies
    integration tests by avoiding file I/O and side effects on a Distribution.

    Parameters:
        dist_name: Optional distribution name (used for overrides and env scoping)
        pyproject_data: Parsed PyProjectData (may be constructed via for_testing())
        overrides: Optional override configuration (same keys as [tool.setuptools_scm])
        force_write_version_files: When True, apply write_to/version_file effects

    Returns:
        The computed version string.
    """
    from vcs_versioning._version_inference import (
        infer_version_string as _vcs_infer_version_string,
    )

    # Delegate to vcs_versioning implementation
    return _vcs_infer_version_string(
        dist_name,
        pyproject_data,
        overrides,
        force_write_version_files=force_write_version_files,
    )


def get_version_inference_config(
    dist_name: str | None,
    current_version: str | None,
    pyproject_data: PyProjectData,
    overrides: dict[str, Any] | None = None,
) -> VersionInferenceResult:
    """
    Determine whether and how to perform version inference.

    Args:
        dist_name: The distribution name
        current_version: Current version if any
        pyproject_data: PyProjectData from parser (None if file doesn't exist)
        overrides: Override configuration (None for no overrides)

    Returns:
        VersionInferenceResult with the decision and configuration
    """

    config = VersionInferenceConfig(
        dist_name=dist_name,
        pyproject_data=pyproject_data,
        overrides=overrides,
    )

    inference_implied = should_infer(pyproject_data) or overrides is not None

    if inference_implied:
        if current_version is None:
            return config
        else:
            return VersionAlreadySetWarning(dist_name)
    else:
        return VersionInferenceNoOp()
