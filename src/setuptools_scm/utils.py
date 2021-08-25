import inspect
import os
import platform
import shlex
import subprocess
import warnings
from typing import cast
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import TYPE_CHECKING
from typing import Union

from ._trace import DEBUG
from ._trace import trace

IS_WINDOWS = platform.system() == "Windows"

if TYPE_CHECKING:
    CompletedProcess = subprocess.CompletedProcess[str]
else:
    try:
        CompletedProcess = subprocess.CompletedProcess[str]
    except TypeError:
        CompletedProcess = subprocess.CompletedProcess


def no_git_env(env) -> Mapping[str, str]:
    # adapted from pre-commit
    # Too many bugs dealing with environment variables and GIT:
    # https://github.com/pre-commit/pre-commit/issues/300
    # In git 2.6.3 (maybe others), git exports GIT_WORK_TREE while running
    # pre-commit hooks
    # In git 1.9.1 (maybe others), git exports GIT_DIR and GIT_INDEX_FILE
    # while running pre-commit hooks in submodules.
    # GIT_DIR: Causes git clone to clone wrong thing
    # GIT_INDEX_FILE: Causes 'error invalid object ...' during commit
    trace("git vars filtered", {k: v for k, v in env.items() if k.startswith("GIT_")})
    return {
        k: v
        for k, v in env.items()
        if not k.startswith("GIT_")
        or k in ("GIT_EXEC_PATH", "GIT_SSH", "GIT_SSH_COMMAND")
    }


def run(
    cmd: Union[str, Sequence[str]],
    cwd: str = ".",
    strip_output: bool = True,
    show_error: bool = False,
) -> CompletedProcess:
    trace("run shell command", cmd, cwd=cwd)
    if os.name == "posix" and isinstance(cmd, str):
        cmd = shlex.split(cmd)
    env: Mapping[str, str] = dict(
        no_git_env(os.environ),
        # os.environ,
        # try to disable i18n
        LC_ALL="C",
        LANGUAGE="",
        HGPLAIN="1",
    )

    res = subprocess.run(
        cmd,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        cwd=cwd,
        encoding="utf-8",
        errors="surrogate-escape",
        env=env,
    )  # type: ignore

    if strip_output:
        if res.stdout:
            res.stdout = res.stdout.strip()
        if res.stderr:
            res.stderr = res.stderr.strip()
    trace(
        "results",
        returncode=res.returncode,
        stdout=res.stdout,
        stderr=res.stderr,
        indent=2,
    )
    if res.returncode and not DEBUG and show_error:
        print(res.stderr)
    return cast(CompletedProcess, res)


def do_ex(cmd, cwd="."):
    p = run(cmd, cwd, show_error=False)
    return p.stdout, p.stderr, p.returncode


def do(cmd, cwd="."):
    return run(cmd, cwd).stdout


def data_from_mime(path):
    with open(path, encoding="utf-8") as fp:
        content = fp.read()
    trace("content", content)
    # the complex conditions come from reading pseudo-mime-messages
    data = dict(x.split(": ", 1) for x in content.splitlines() if ": " in x)
    trace("data", data)
    return data


def function_has_arg(fn, argname):
    assert inspect.isfunction(fn)

    argspec = inspect.signature(fn).parameters

    return argname in argspec


def has_command(name, warn=True):
    try:
        p = subprocess.run(
            [name, "help"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except OSError:
        res = False
    else:
        res = not p.returncode
    if not res and warn:
        warnings.warn("%r was not found" % name, category=RuntimeWarning)
    return res


def require_command(name):
    if not has_command(name, warn=False):
        raise OSError("%r was not found" % name)


try:
    from importlib.metadata import entry_points  # type: ignore
except ImportError:
    from pkg_resources import iter_entry_points
else:

    def iter_entry_points(group: str, name: Optional[str] = None):
        eps = entry_points()[group]
        if name is None:
            return iter(eps)
        return (ep for ep in eps if ep.name == name)
