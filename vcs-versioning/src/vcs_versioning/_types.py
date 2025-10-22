from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from . import _version_schemes as version

PathT: TypeAlias = "os.PathLike[str]" | str

CMD_TYPE: TypeAlias = Sequence[PathT] | str

VERSION_SCHEME: TypeAlias = str | Callable[["version.ScmVersion"], str]
VERSION_SCHEMES: TypeAlias = list[str] | tuple[str, ...] | VERSION_SCHEME
SCMVERSION: TypeAlias = "version.ScmVersion"

# Git pre-parse function types
GIT_PRE_PARSE: TypeAlias = str | None
