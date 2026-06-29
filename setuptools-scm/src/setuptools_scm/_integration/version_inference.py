from __future__ import annotations

import logging
import sys

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any
from typing import Protocol
from typing import cast

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

from setuptools import Distribution
from setuptools import sic as setuptools_sic
from vcs_versioning._pyproject_reading import PyProjectData
from vcs_versioning._version_cls import NonNormalizedVersion

if TYPE_CHECKING:
    from vcs_versioning import _config
    from vcs_versioning._environment import VcsEnvironment
    from vcs_versioning._scm_version import ScmVersion

from .build_py import VersionInferenceData
from .build_py import set_version_inference_data
from .pyproject_reading import should_infer

log = logging.getLogger(__name__)

_FALSY_VALUES = frozenset(("0", "false", "no"))


def _should_write_to_source(config: _config.Configuration) -> bool:
    """Check if version files should be written to source at inference time.

    Resolution order:

    1. **Environment variable** (``SETUPTOOLS_SCM_WRITE_TO_SOURCE`` /
       ``VCS_VERSIONING_WRITE_TO_SOURCE``) — highest priority, no warning.
    2. **pyproject.toml** ``write_to_source`` option — explicit opt-in/out,
       no warning.
    3. **Unset** (neither env var nor config) — write to source **and** emit
       a ``DeprecationWarning`` advising the user to set the option
       explicitly, since the default will change in the next major release.
    """
    import warnings

    reader = config.env.make_reader(config.dist_name)
    env_value = reader.read("WRITE_TO_SOURCE")

    if env_value is not None:
        return env_value.lower() not in _FALSY_VALUES

    if config.write_to_source is not None:
        return config.write_to_source

    warnings.warn(
        "setuptools-scm writes version files to the source tree by default, "
        "but this will change in a future major release. "
        "Set 'write_to_source = true' (to keep current behavior) or "
        "'write_to_source = false' (to only write to the build directory) "
        "in [tool.setuptools_scm] in pyproject.toml to silence this warning. "
        "You can also set the SETUPTOOLS_SCM_WRITE_TO_SOURCE environment variable.",
        DeprecationWarning,
        stacklevel=3,
    )
    return True


def infer_version_with_config(
    dist_name: str | None,
    pyproject_data: PyProjectData,
    overrides: dict[str, Any] | None = None,
    *,
    env: VcsEnvironment | None = None,
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
    from vcs_versioning._environment import VcsEnvironment as _VcsEnvironment
    from vcs_versioning._get_version_impl import _version_missing
    from vcs_versioning._get_version_impl import write_version_files
    from vcs_versioning._legacy_parse import has_legacy_parse_eps
    from vcs_versioning._legacy_parse import parse_fallback_version
    from vcs_versioning._legacy_parse import parse_scm_version
    from vcs_versioning._overrides import _apply_metadata_overrides
    from vcs_versioning._overrides import _read_pretended_version_for
    from vcs_versioning._version_schemes import format_version

    if env is None:
        env = _VcsEnvironment.from_env("SETUPTOOLS_SCM")
    config = env.build_config(
        dist_name=dist_name, pyproject_data=pyproject_data, **(overrides or {})
    )

    workdir = None
    scm_version: ScmVersion | None = None

    pretended = _read_pretended_version_for(config)
    if pretended is not None:
        scm_version = pretended
    else:
        workdir = config.discover_workdir()
        if workdir is not None:
            scm_version = workdir.get_scm_version()

        if scm_version is None and has_legacy_parse_eps():
            scm_version = parse_scm_version(config) or parse_fallback_version(config)

    if scm_version is None:
        _version_missing(config, tool=env.tool_names[0])

    scm_version = _apply_metadata_overrides(scm_version, config)
    assert scm_version is not None
    version_string = format_version(scm_version)

    if _should_write_to_source(config):
        try:
            write_version_files(config, version=version_string, scm_version=scm_version)
        except OSError as e:
            log.warning(
                "Could not write version file to source tree: %s. "
                "The file will still be written to the build directory during build.",
                e,
            )

    return VersionInferenceData(
        version=version_string,
        config=config,
        scm_version=scm_version,
        workdir=workdir,
    )


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
    env: VcsEnvironment | None = None

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
            env=self.env,
        )
        # When normalize=False, wrap in setuptools.sic() to prevent
        # setuptools' _normalize_version from re-normalizing (stripping
        # CalVer zero-padding, etc.) after our hook returns.
        if issubclass(data.config.version_cls, NonNormalizedVersion):
            dist.metadata.version = setuptools_sic(data.version)
        else:
            dist.metadata.version = data.version

        # Store version inference data for build_py to write to build directory
        set_version_inference_data(dist, data)
        log.debug(
            "Stored version inference data for build_py: version=%s", data.version
        )

        # Mark that this version was set by infer_version if overrides is None (infer_version context)
        if self.overrides is None:
            from .build_py import _DistWithScm

            cast(_DistWithScm, dist)._setuptools_scm_version_set_by_infer = True


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
    "VersionInferenceConfig | VersionAlreadySetWarning | VersionInferenceNoOp"
)


def infer_version_string(
    dist_name: str | None,
    pyproject_data: PyProjectData,
    overrides: dict[str, Any] | None = None,
    *,
    force_write_version_files: bool = False,
    env: VcsEnvironment | None = None,
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
        env: Optional VcsEnvironment. If None, resolves one with SETUPTOOLS_SCM prefix.

    Returns:
        The computed version string.
    """
    from vcs_versioning._environment import VcsEnvironment as _VcsEnvironment
    from vcs_versioning._version_inference import (
        infer_version_string as _vcs_infer_version_string,
    )

    if env is None:
        env = _VcsEnvironment.from_env("SETUPTOOLS_SCM")

    return _vcs_infer_version_string(
        dist_name,
        pyproject_data,
        overrides,
        force_write_version_files=force_write_version_files,
        env=env,
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
