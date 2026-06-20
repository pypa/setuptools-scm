"""Shared version-metadata contract.

Defines the minimal set of fields that all version-data representations
(live ``ScmVersion``, serialized ``ScmVersionData``, env-override
``PretendMetadataDict``) have in common.  Used to type boundaries that
accept any of these without circular imports.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable


@runtime_checkable
class VersionFields(Protocol):
    """Minimal VCS version metadata -- the shared contract.

    Both ``ScmVersion`` (live) and ``ScmVersionData`` (serialized) satisfy
    this protocol structurally.
    """

    @property
    def tag(self) -> str: ...

    @property
    def distance(self) -> int: ...

    @property
    def node(self) -> str | None: ...

    @property
    def dirty(self) -> bool: ...

    @property
    def branch(self) -> str | None: ...

    @property
    def node_date(self) -> date | str | None: ...
