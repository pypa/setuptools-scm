from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from . import _version_schemes as version

# Re-export from _compat for backward compatibility
from ._compat import PathT as PathT  # noqa: PLC0414

__all__ = [
    "PathT",
    "CMD_TYPE",
    "VERSION_SCHEME",
    "VERSION_SCHEMES",
    "SCMVERSION",
    "GIT_PRE_PARSE",
]

CMD_TYPE: TypeAlias = Sequence[PathT] | str

VERSION_SCHEME: TypeAlias = str | Callable[["version.ScmVersion"], str]
VERSION_SCHEMES: TypeAlias = list[str] | tuple[str, ...] | VERSION_SCHEME
SCMVERSION: TypeAlias = "version.ScmVersion"

# Git pre-parse function types
GIT_PRE_PARSE: TypeAlias = str | None
