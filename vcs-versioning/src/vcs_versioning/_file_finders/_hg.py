from __future__ import annotations

import logging
import os
import subprocess

from .. import _types as _t
from .._backends._hg import run_hg
from .._compat import norm_real
from .._integration import data_from_mime
from . import collect_files_and_dirs, is_toplevel_acceptable, scm_find_files

log = logging.getLogger(__name__)


def _hg_toplevel(path: str) -> str | None:
    try:
        return run_hg(
            ["root"],
            cwd=(path or "."),
            check=True,
        ).parse_success(norm_real)
    except subprocess.CalledProcessError:
        # hg returned error, we are not in a mercurial repo
        return None
    except OSError:
        # hg command not found, probably
        return None


def _hg_ls_files_and_dirs(
    toplevel: str,
    *,
    hg_command: str | None = None,
    timeout: int | None = None,
) -> tuple[set[str], set[str]]:
    res = run_hg(["files"], cwd=toplevel, hg_command=hg_command, timeout=timeout)
    if res.returncode:
        return set(), set()
    return collect_files_and_dirs(res.stdout.splitlines(), toplevel)


def hg_find_files(path: str = "") -> list[str]:
    """Find files tracked in a Mercurial repository"""
    toplevel = _hg_toplevel(path)
    if not is_toplevel_acceptable(toplevel):
        return []
    assert toplevel is not None
    hg_files, hg_dirs = _hg_ls_files_and_dirs(toplevel)
    return scm_find_files(path, hg_files, hg_dirs)


def hg_archive_find_files(path: _t.PathT = "") -> list[str]:
    """Find files in a Mercurial archive (all files, since archive already filtered)"""
    # This function assumes that ``path`` is obtained from a mercurial archive
    # and therefore all the files that should be ignored were already removed.
    archival = os.path.join(path, ".hg_archival.txt")
    if not os.path.exists(archival):
        return []

    data = data_from_mime(archival)

    if "node" not in data:
        # Ensure file is valid
        return []

    log.warning("hg archive detected - fallback to listing all files")
    return scm_find_files(path, set(), set(), force_all_files=True)


__all__ = ["hg_find_files", "hg_archive_find_files"]
