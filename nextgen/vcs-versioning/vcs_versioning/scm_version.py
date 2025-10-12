"""ScmVersion class and related utilities (public API)"""

from __future__ import annotations

# For now, re-export from _version_schemes
# TODO: Extract ScmVersion and its core helpers into this module
from ._version_schemes import ScmVersion
from ._version_schemes import VersionExpectations
from ._version_schemes import callable_or_entrypoint
from ._version_schemes import meta
from ._version_schemes import mismatches
from ._version_schemes import tag_to_version

__all__ = [
    "ScmVersion",
    "VersionExpectations",
    "callable_or_entrypoint",
    "meta",
    "mismatches",
    "tag_to_version",
]
