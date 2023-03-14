"""
utils
"""
from __future__ import annotations

import logging
import subprocess
import sys
import warnings
from types import CodeType
from types import FunctionType
from typing import NamedTuple
from typing import TYPE_CHECKING

from . import _run_cmd
from . import _trace

if TYPE_CHECKING:
    from . import _types as _t

log = logging.getLogger(__name__)


class _CmdResult(NamedTuple):
    out: str
    err: str
    returncode: int


def do_ex(cmd: _t.CMD_TYPE, cwd: _t.PathT = ".") -> _CmdResult:
    res = _run_cmd.run(cmd, cwd)
    return _CmdResult(res.stdout, res.stderr, res.returncode)


def do(cmd: _t.CMD_TYPE, cwd: _t.PathT = ".") -> str:
    out, err, ret = do_ex(cmd, cwd)
    if ret and not _trace.DEBUG:
        print(err)
    return out


def data_from_mime(path: _t.PathT) -> dict[str, str]:
    with open(path, encoding="utf-8") as fp:
        content = fp.read()
    _trace.trace("content", repr(content))
    # the complex conditions come from reading pseudo-mime-messages
    data = dict(x.split(": ", 1) for x in content.splitlines() if ": " in x)
    _trace.trace("data", data)
    return data


def function_has_arg(fn: object | FunctionType, argname: str) -> bool:
    assert isinstance(fn, FunctionType)
    code: CodeType = fn.__code__
    return argname in code.co_varnames


def has_command(name: str, args: list[str] | None = None, warn: bool = True) -> bool:
    try:
        cmd = [name, "help"] if args is None else [name, *args]
        p = _run_cmd.run(cmd, cwd=".", timeout=5)
    except OSError:
        _trace.trace(*sys.exc_info())
        res = False
    except subprocess.TimeoutExpired as e:
        log.info(e)
        _trace.trace(e)
        res = False

    else:
        res = not p.returncode
    if not res and warn:
        warnings.warn("%r was not found" % name, category=RuntimeWarning)
    return res


def require_command(name: str) -> None:
    if not has_command(name, warn=False):
        raise OSError(f"{name!r} was not found")
