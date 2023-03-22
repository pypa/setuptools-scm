from __future__ import annotations

from pathlib import Path
from typing import ClassVar
from typing import TYPE_CHECKING

from .utils import require_command

if TYPE_CHECKING:
    from . import _types as _t


class Workdir:
    COMMAND: ClassVar[str]
    path: Path

    def __init__(self, path: _t.PathT):
        require_command(self.COMMAND)
        self.path = Path(path)
