from __future__ import annotations

import os
import sys
from typing import Any
from typing import Callable
from typing import List
from typing import NamedTuple
from typing import Protocol
from typing import TYPE_CHECKING
from typing import TypeVar
from typing import Union


if TYPE_CHECKING:
    from setuptools_scm import version

if sys.version_info >= (3, 9):
    from typing import ParamSpec, TypeAlias
else:
    from typing_extensions import ParamSpec, TypeAlias

PathT = Union["os.PathLike[str]", str]

CMD_TYPE: TypeAlias = Union[List[str], str]

VERSION_SCHEME = Union[str, Callable[["version.ScmVersion"], str]]


class CmdResult(NamedTuple):
    out: str
    err: str
    returncode: int


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
