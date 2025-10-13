from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Protocol, TypeAlias, Union

if TYPE_CHECKING:
    from setuptools import Distribution

    from . import _version_schemes as version
    from ._pyproject_reading import PyProjectData
    from ._toml import InvalidTomlError

PathT: TypeAlias = Union["os.PathLike[str]", str]

CMD_TYPE: TypeAlias = Sequence[PathT] | str

VERSION_SCHEME: TypeAlias = str | Callable[["version.ScmVersion"], str]
VERSION_SCHEMES: TypeAlias = list[str] | tuple[str, ...] | VERSION_SCHEME
SCMVERSION: TypeAlias = "version.ScmVersion"

# Git pre-parse function types
GIT_PRE_PARSE: TypeAlias = str | None

# Testing injection types for configuration reading
GivenPyProjectResult: TypeAlias = Union[
    "PyProjectData", "InvalidTomlError", FileNotFoundError, None
]


class VersionInferenceApplicable(Protocol):
    """A result object from version inference decision that can be applied to a dist."""

    def apply(self, dist: Distribution) -> None:  # pragma: no cover - structural type
        ...


class GetVersionInferenceConfig(Protocol):
    """Callable protocol for the decision function used by integration points."""

    def __call__(
        self,
        dist_name: str | None,
        current_version: str | None,
        pyproject_data: PyProjectData,
        overrides: dict[str, object] | None = None,
    ) -> VersionInferenceApplicable:  # pragma: no cover - structural type
        ...
