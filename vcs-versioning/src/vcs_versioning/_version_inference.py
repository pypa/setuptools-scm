"""Core version inference functionality for build tool integrations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ._pyproject_reading import PyProjectData


def infer_version_string(
    dist_name: str | None,
    pyproject_data: PyProjectData,
    overrides: dict[str, Any] | None = None,
    *,
    force_write_version_files: bool = False,
) -> str:
    """
    Compute the inferred version string from the given inputs.

    This is a pure helper that avoids requiring build-tool specific
    distribution objects, making it easier to test and reuse across
    different build systems.

    Parameters:
        dist_name: Optional distribution name (used for overrides and env scoping)
        pyproject_data: Parsed PyProjectData (may be constructed via for_testing())
        overrides: Optional override configuration (same keys as [tool.setuptools_scm])
        force_write_version_files: When True, apply write_to/version_file effects

    Returns:
        The computed version string.

    Raises:
        SystemExit: If version cannot be determined (via _version_missing)
    """
    from ._config import Configuration
    from ._get_version_impl import _get_version, _version_missing

    config = Configuration.from_file(
        dist_name=dist_name, pyproject_data=pyproject_data, **(overrides or {})
    )

    maybe_version = _get_version(
        config, force_write_version_files=force_write_version_files
    )
    if maybe_version is None:
        _version_missing(config)
    return maybe_version


__all__ = ["infer_version_string"]
