from __future__ import annotations

import os
from typing import Callable
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import TYPE_CHECKING
from typing import Union


if TYPE_CHECKING:
    from typing_extensions import TypeAlias
    from . import version

PathT: TypeAlias = Union["os.PathLike[str]", str]

CMD_TYPE: TypeAlias = Union[Sequence[PathT], str]

VERSION_SCHEME: TypeAlias = Union[str, Callable[["version.ScmVersion"], str]]
VERSION_SCHEMES: TypeAlias = Union[List[str], Tuple[str, ...], VERSION_SCHEME]
SCMVERSION: TypeAlias = "version.ScmVersion"


class Result:
    """ Just like a normal bool, but with a slot for a message """
    def __init__(self, status: bool, message: Optional[str] = None):
        self.status: bool = status
        self.message: str = message or ""

    def __bool__(self) -> bool:
        return self.status
