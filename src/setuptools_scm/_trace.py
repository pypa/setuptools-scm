import os
import sys
import traceback
from typing import List
from typing import Optional

DEBUG = bool(os.environ.get("SETUPTOOLS_SCM_DEBUG"))


def trace(
    key: str,
    var: Optional[object] = None,
    *,
    indent: int = 1,
    **kw: object,
) -> None:
    if DEBUG:

        if var or kw or var == 0:
            print("  " * (indent - 1), end="")
            print(key, end=": ")

        if not var and var != 0:
            if kw and any(kw.values()):
                print()
        else:
            if isinstance(var, tuple):
                _trace_maybe_named_tuple(indent, var)
            elif isinstance(var, str):
                _trace_str(var, indent)
            elif isinstance(var, dict):
                print()
                _trace_items(
                    var,
                    indent,
                )
            else:
                print(var)
        _trace_items(kw, indent)

        sys.stdout.flush()


def _trace_items(var, indent):
    for k, v in var.items():
        trace(k, v, indent=indent + 1)


def _trace_str(var, indent):
    var = var.strip()
    lines = var.splitlines()
    if len(lines) == 1:
        print(lines[0])
    else:
        print()
        for line in lines:
            print("  " * indent, line)


def _trace_maybe_named_tuple(indent, var):
    fields: List[str] = getattr(var, "_fields", [])
    if fields:
        print(type(var).name)
        for name in fields:
            trace(name, getattr(var, name), indent=indent + 1)
    else:
        print(var)


def trace_exception() -> None:
    if DEBUG:
        traceback.print_exc()
