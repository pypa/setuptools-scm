from __future__ import annotations

import os

from .. import _types as _t


def norm_real(path: _t.PathT) -> str:
    """Normalize and resolve a path (combining normcase and realpath)"""
    return os.path.normcase(os.path.realpath(path))
