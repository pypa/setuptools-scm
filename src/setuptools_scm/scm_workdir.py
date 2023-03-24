from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from . import _types as _t


class Workdir:
    path: Path

    def __init__(self, path: _t.PathT):
        self.path = Path(path)
