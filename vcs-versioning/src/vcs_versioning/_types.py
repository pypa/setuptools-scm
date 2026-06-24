from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Union

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

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

if TYPE_CHECKING:
    CMD_TYPE: TypeAlias = Sequence[PathT] | str
    VERSION_SCHEME_CALLABLE: TypeAlias = Callable[["ScmVersion"], str | None]
    VERSION_SCHEME: TypeAlias = str | VERSION_SCHEME_CALLABLE
    VERSION_SCHEMES: TypeAlias = Sequence[VERSION_SCHEME] | VERSION_SCHEME
    GIT_PRE_PARSE: TypeAlias = str | None
else:
    CMD_TYPE = Union[Sequence, str]
    VERSION_SCHEME_CALLABLE = Callable
    VERSION_SCHEME = Union[str, Callable]
    VERSION_SCHEMES = Union[Sequence, str, Callable]
    GIT_PRE_PARSE = Union[str, None]

SCMVERSION: TypeAlias = "ScmVersion"
