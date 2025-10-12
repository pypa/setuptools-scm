"""Re-export _get_version from vcs_versioning and add setuptools-specific wrappers"""

from __future__ import annotations

from os import PathLike

from vcs_versioning._get_version_impl import _find_scm_in_parents
from vcs_versioning._get_version_impl import _get_version
from vcs_versioning._get_version_impl import _version_missing
from vcs_versioning._get_version_impl import parse_fallback_version
from vcs_versioning._get_version_impl import parse_scm_version
from vcs_versioning._get_version_impl import parse_version
from vcs_versioning._get_version_impl import write_version_files


# Legacy get_version function (soft deprecated)
def get_version(root: str | PathLike[str] | None = None, **kwargs: object) -> str:
    """Legacy API - get version string

    This function is soft deprecated. Use Configuration.from_file() and _get_version() instead.

    Args:
        root: Optional root directory (can be passed as positional arg for backward compat)
        **kwargs: Additional configuration parameters
    """
    from vcs_versioning._get_version_impl import get_version as _vcs_get_version

    if root is not None:
        kwargs["root"] = root
    # Delegate to vcs_versioning's get_version which handles all validation including tag_regex
    return _vcs_get_version(**kwargs)  # type: ignore[arg-type]


__all__ = [
    "_find_scm_in_parents",
    "_get_version",
    "_version_missing",
    "get_version",
    "parse_fallback_version",
    "parse_scm_version",
    "parse_version",
    "write_version_files",
]
