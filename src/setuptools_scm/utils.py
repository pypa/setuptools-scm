"""
utils
"""
from __future__ import annotations

import os
import platform
import shlex
import subprocess
import sys
import warnings
from types import CodeType
from types import FunctionType
from typing import Iterator
from typing import Mapping
from typing import NamedTuple
from typing import TYPE_CHECKING

if TYPE_CHECKING:

    from . import _types as _t

DEBUG = bool(os.environ.get("SETUPTOOLS_SCM_DEBUG"))
IS_WINDOWS = platform.system() == "Windows"


class _CmdResult(NamedTuple):
    out: str
    err: str
    returncode: int


def no_git_env(env: Mapping[str, str]) -> dict[str, str]:
    # adapted from pre-commit
    # Too many bugs dealing with environment variables and GIT:
    # https://github.com/pre-commit/pre-commit/issues/300
    # In git 2.6.3 (maybe others), git exports GIT_WORK_TREE while running
    # pre-commit hooks
    # In git 1.9.1 (maybe others), git exports GIT_DIR and GIT_INDEX_FILE
    # while running pre-commit hooks in submodules.
    # GIT_DIR: Causes git clone to clone wrong thing
    # GIT_INDEX_FILE: Causes 'error invalid object ...' during commit
    for k, v in env.items():
        if k.startswith("GIT_"):
            trace(k, v)
    return {
        k: v
        for k, v in env.items()
        if not k.startswith("GIT_")
        or k in ("GIT_EXEC_PATH", "GIT_SSH", "GIT_SSH_COMMAND")
    }


def trace(*k: object) -> None:
    if DEBUG:
        print(*k, file=sys.stderr, flush=True)


def ensure_stripped_str(str_or_bytes: str | bytes) -> str:
    if isinstance(str_or_bytes, str):
        return str_or_bytes.strip()
    else:
        return str_or_bytes.decode("utf-8", "surrogateescape").strip()


def _run(cmd: _t.CMD_TYPE, cwd: _t.PathT) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        cmd,
        capture_output=True,
        cwd=str(cwd),
        env=dict(
            no_git_env(os.environ),
            # os.environ,
            # try to disable i18n
            LC_ALL="C",
            LANGUAGE="",
            HGPLAIN="1",
        ),
    )


def do_ex(cmd: _t.CMD_TYPE, cwd: _t.PathT = ".") -> _CmdResult:
    trace("cmd", repr(cmd))
    trace(" in", cwd)
    if os.name == "posix" and not isinstance(cmd, (list, tuple)):
        cmd = shlex.split(cmd)

    res = _run(cmd, cwd)
    if res.stdout:
        trace("out", repr(res.stdout))
    if res.stderr:
        trace("err", repr(res.stderr))
    if res.returncode:
        trace("ret", res.returncode)
    return _CmdResult(
        ensure_stripped_str(res.stdout), ensure_stripped_str(res.stderr), res.returncode
    )


def do(cmd: list[str] | str, cwd: str | _t.PathT = ".") -> str:
    out, err, ret = do_ex(cmd, cwd)
    if ret:
        print(err)
    return out


def data_from_mime(path: _t.PathT) -> dict[str, str]:
    with open(path, encoding="utf-8") as fp:
        content = fp.read()
    trace("content", repr(content))
    # the complex conditions come from reading pseudo-mime-messages
    data = dict(x.split(": ", 1) for x in content.splitlines() if ": " in x)
    trace("data", data)
    return data


def function_has_arg(fn: object | FunctionType, argname: str) -> bool:
    assert isinstance(fn, FunctionType)
    code: CodeType = fn.__code__
    return argname in code.co_varnames


def has_command(name: str, args: list[str] | None = None, warn: bool = True) -> bool:
    try:
        cmd = [name, "help"] if args is None else [name, *args]
        p = _run(cmd, ".")
    except OSError:
        trace(*sys.exc_info())
        res = False
    else:
        res = not p.returncode
    if not res and warn:
        warnings.warn("%r was not found" % name, category=RuntimeWarning)
    return res


def require_command(name: str) -> None:
    if not has_command(name, warn=False):
        raise OSError("%r was not found" % name)


def iter_entry_points(
    group: str, name: str | None = None
) -> Iterator[_t.EntrypointProtocol]:

    from ._entrypoints import iter_entry_points

    return iter_entry_points(group, name)
