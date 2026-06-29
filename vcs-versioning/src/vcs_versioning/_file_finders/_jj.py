"""File finder for Jujutsu (jj) repositories.

Uses ``jj file list`` to enumerate tracked files, analogous to
``git ls-files`` in the git file finder.
"""

from __future__ import annotations

import logging
import os
import subprocess

from .. import _types as _t
from .._compat import norm_real
from .._run_cmd import run as _run
from . import collect_files_and_dirs, is_toplevel_acceptable, scm_find_files

log = logging.getLogger(__name__)


def _jj_toplevel(path: str) -> str | None:
    try:
        cwd = os.path.abspath(path or ".")
        res = _run(["jj", "root", "--no-pager"], cwd=cwd)
        if res.returncode:
            return None
        toplevel = res.stdout.strip()
        if not toplevel:
            return None
        return norm_real(toplevel)
    except subprocess.CalledProcessError:
        return None
    except OSError:
        return None


def _jj_ls_files_and_dirs(
    toplevel: str, *, timeout: int | None = None
) -> tuple[set[str], set[str]]:
    """List tracked files via ``jj file list``.

    Returns ``(files, dirs)`` sets with absolute, normcase'd paths --
    matching the contract of ``_git_ls_files_and_dirs``.
    """
    res = _run(
        ["jj", "file", "list", "--no-pager"],
        cwd=toplevel,
        timeout=timeout,
    )
    if res.returncode:
        log.error("listing jj files failed - pretending there aren't any")
        return set(), set()

    return collect_files_and_dirs(res.stdout.strip().split("\n"), toplevel)


def jj_find_files(path: _t.PathT = "") -> list[str]:
    """Find files tracked in a Jujutsu repository."""
    toplevel = _jj_toplevel(os.fspath(path))
    if not is_toplevel_acceptable(toplevel):
        return []
    fullpath = norm_real(path)
    if not fullpath.startswith(toplevel):
        log.warning("toplevel mismatch computed %s vs resolved %s", toplevel, fullpath)
    jj_files, jj_dirs = _jj_ls_files_and_dirs(toplevel)
    return scm_find_files(path, jj_files, jj_dirs)


__all__ = ["jj_find_files"]
