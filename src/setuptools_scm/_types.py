import os
from typing import Callable
from typing import TYPE_CHECKING
from typing import TypeVar
from typing import Union

if TYPE_CHECKING:

    from typing_extensions import ParamSpec
else:

    class ParamSpec(list):
        def __init__(self, _) -> None:
            pass


PathT = Union["os.PathLike[str]", str]


T = TypeVar("T")
T2 = TypeVar("T2")
PARAMS = ParamSpec("PARAMS")


def transfer_input_args(
    template: "Callable[PARAMS, T]",
) -> Callable[[Callable[..., T2]], "Callable[PARAMS, T2]"]:
    def decorate(func: Callable[..., T2]) -> "Callable[PARAMS, T2]":
        return func

    return decorate
