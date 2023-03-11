from __future__ import annotations

import os
import sys
import textwrap
from typing import Sequence

from . import _types as _t

DEBUG: bool = bool(os.environ.get("SETUPTOOLS_SCM_DEBUG"))


def trace(*k: object, indent: bool = False) -> None:
    if not DEBUG:
        if indent and len(k) > 1:
            k = (k[0],) + tuple(textwrap.indent(str(s), "    ") for s in k[1:])
        print(*k, file=sys.stderr, flush=True)


def _unsafe_quote_for_display(item: _t.PathT) -> str:
    # give better results than shlex.join in our cases
    text = os.fspath(item)
    return text if all(c not in text for c in " {[:") else f'"{text}"'


def trace_command(cmd: Sequence[_t.PathT], cwd: _t.PathT) -> None:
    if not DEBUG:
        return
    cmd_4_trace = " ".join(map(_unsafe_quote_for_display, cmd))
    trace(f"---\n > {cwd}\\$ ", cmd_4_trace, indent=True)
