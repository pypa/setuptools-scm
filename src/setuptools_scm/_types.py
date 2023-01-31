from __future__ import annotations

import os
from typing import Any
from typing import Callable
from typing import List
from typing import Tuple
from typing import TypeVar
from typing import Union

from typing_extensions import ParamSpec
from typing_extensions import Protocol
from typing_extensions import TypeAlias

from . import version

PathT: TypeAlias = Union["os.PathLike[str]", str]

CMD_TYPE: TypeAlias = Union[List[str], str]

VERSION_SCHEME: TypeAlias = Union[str, Callable[["version.ScmVersion"], str]]
VERSION_SCHEMES: TypeAlias = Union[List[str], Tuple[str, ...], VERSION_SCHEME]
SCMVERSION: TypeAlias = "version.ScmVersion"


class EntrypointProtocol(Protocol):
    name: str

    def load(self) -> Any:
        pass


T = TypeVar("T")
T2 = TypeVar("T2")
P = ParamSpec("P")


def transfer_input_args(
    template: Callable[P, T],
) -> Callable[[Callable[..., T]], Callable[P, T]]:
    def decorate(func: Callable[..., T2]) -> Callable[P, T2]:
        return func

    return decorate
