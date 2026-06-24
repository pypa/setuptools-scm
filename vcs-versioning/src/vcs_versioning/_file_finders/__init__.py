from __future__ import annotations

import logging
import os
import sys
from collections.abc import Callable, Mapping

if sys.version_info >= (3, 10):
    from typing import TypeGuard
else:
    from typing_extensions import TypeGuard

from .. import _types as _t
from .._compat import norm_real
from .._entrypoints import entry_points

log = logging.getLogger("vcs_versioning.file_finder")


def scm_find_files(
    path: _t.PathT,
    scm_files: set[str],
    scm_dirs: set[str],
    force_all_files: bool = False,
) -> list[str]:
    """Core file discovery logic that follows symlinks

    - path: the root directory from which to search
    - scm_files: set of scm controlled files and symlinks
      (including symlinks to directories)
    - scm_dirs: set of scm controlled directories
      (including directories containing no scm controlled files)
    - force_all_files: ignore ``scm_files`` and ``scm_dirs`` and list everything.

    scm_files and scm_dirs must be absolute with symlinks resolved (realpath),
    with normalized case (normcase)
    """
    realpath = norm_real(path)
    seen: set[str] = set()
    res: list[str] = []
    for dirpath, dirnames, filenames in os.walk(realpath, followlinks=True):
        # dirpath with symlinks resolved
        realdirpath = norm_real(dirpath)

        def _link_not_in_scm(n: str, realdirpath: str = realdirpath) -> bool:
            fn = os.path.join(realdirpath, os.path.normcase(n))
            return os.path.islink(fn) and fn not in scm_files

        if not force_all_files and realdirpath not in scm_dirs:
            # directory not in scm, don't walk it's content
            dirnames[:] = []
            continue
        if os.path.islink(dirpath) and not os.path.relpath(
            realdirpath, realpath
        ).startswith(os.pardir):
            # a symlink to a directory not outside path:
            # we keep it in the result and don't walk its content
            res.append(os.path.join(path, os.path.relpath(dirpath, path)))
            dirnames[:] = []
            continue
        if realdirpath in seen:
            # symlink loop protection
            dirnames[:] = []
            continue
        dirnames[:] = [
            dn for dn in dirnames if force_all_files or not _link_not_in_scm(dn)
        ]
        for filename in filenames:
            if not force_all_files and _link_not_in_scm(filename):
                continue
            # dirpath + filename with symlinks preserved
            fullfilename = os.path.join(dirpath, filename)
            is_tracked = norm_real(fullfilename) in scm_files
            if force_all_files or is_tracked:
                res.append(os.path.join(path, os.path.relpath(fullfilename, realpath)))
        seen.add(realdirpath)
    return res


def _read_ignore_vcs_roots(env: Mapping[str, str] | None = None) -> list[str]:
    """Read IGNORE_VCS_ROOTS from environment variables.

    File finders are invoked via ``setuptools.file_finders`` entry points
    which receive only a path, so they cannot access ``config.env``.
    This function reads directly from the process environment, preferring
    tool names from the active VcsEnvironment when available.
    """
    from ..overrides import EnvReader, get_active_vcs_env

    if env is None:
        env = os.environ
    active_env = get_active_vcs_env()
    tool_names = (
        active_env.tool_names if active_env else ("SETUPTOOLS_SCM", "VCS_VERSIONING")
    )
    reader = EnvReader(tools_names=tool_names, env=env)
    raw = reader.read("IGNORE_VCS_ROOTS", split=os.pathsep, default=[])
    return [os.path.normcase(p) for p in raw]


def is_toplevel_acceptable(
    toplevel: str | None,
    *,
    ignore_vcs_roots: list[str] | None = None,
) -> TypeGuard[str]:
    """Check if a VCS toplevel directory is acceptable (not in ignore list).

    Args:
        toplevel: The VCS toplevel directory to check
        ignore_vcs_roots: Explicit list of roots to ignore. When ``None``,
            reads ``IGNORE_VCS_ROOTS`` from the process environment.
    """
    if toplevel is None:
        return False

    if ignore_vcs_roots is None:
        ignore_vcs_roots = _read_ignore_vcs_roots()

    log.debug(
        "toplevel: %r\n    ignored %s",
        toplevel,
        ignore_vcs_roots,
    )

    return toplevel not in ignore_vcs_roots


def find_files(path: _t.PathT = "") -> list[str]:
    """Discover files using registered file finder entry points."""
    eps = [
        *entry_points(group="setuptools_scm.files_command"),
        *entry_points(group="setuptools_scm.files_command_fallback"),
    ]
    for ep in eps:
        command: Callable[[_t.PathT], list[str]] = ep.load()
        res: list[str] = command(path)
        if res:
            return res

    return []


__all__ = ["scm_find_files", "is_toplevel_acceptable", "find_files"]
