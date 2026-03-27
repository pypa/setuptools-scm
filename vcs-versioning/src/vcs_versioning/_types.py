from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from ._scm_version import ScmVersion

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

VERSION_SCHEME_CALLABLE: TypeAlias = Callable[["ScmVersion"], str | None]
VERSION_SCHEME: TypeAlias = str | VERSION_SCHEME_CALLABLE
VERSION_SCHEMES: TypeAlias = Sequence[VERSION_SCHEME] | VERSION_SCHEME
SCMVERSION: TypeAlias = "ScmVersion"

# Git pre-parse function types
GIT_PRE_PARSE: TypeAlias = str | None
