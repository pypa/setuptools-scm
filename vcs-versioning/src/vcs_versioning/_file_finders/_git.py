from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from .. import _types as _t
from .._backends._git import run_git
from .._compat import norm_real, strip_path_suffix
from .._integration import data_from_mime
from .._run_cmd import run as _run
from . import is_toplevel_acceptable, scm_find_files

log = logging.getLogger(__name__)


def _git_toplevel(path: str) -> str | None:
    try:
        cwd = os.path.abspath(path or ".")
        res = _run(["git", "rev-parse", "HEAD"], cwd=cwd)
        if res.returncode:
            # This catches you being in a git directory, but the
            # permissions being incorrect.  With modern contanizered
            # CI environments you can easily end up in a cloned repo
            # with incorrect permissions and we don't want to silently
            # ignore files.
            if "--add safe.directory" in res.stderr and not os.environ.get(
                "SETUPTOOLS_SCM_IGNORE_DUBIOUS_OWNER"
            ):
                log.error(res.stderr)
                raise SystemExit(
                    "git introspection failed: {}".format(res.stderr.split("\n")[0])
                )
            # BAIL if there is no commit
            log.error("listing git files failed - pretending there aren't any")
            return None
        res = _run(
            ["git", "rev-parse", "--show-prefix"],
            cwd=cwd,
        )
        if res.returncode:
            return None
        out = res.stdout[:-1]  # remove the trailing pathsep
        if not out:
            out = cwd
        else:
            # Here, ``out`` is a relative path to root of git.
            # ``cwd`` is absolute path to current working directory.
            # the below method removes the length of ``out`` from
            # ``cwd``, which gives the git toplevel
            out = strip_path_suffix(cwd, out, f"cwd={cwd!r}\nout={out!r}")
        log.debug("find files toplevel %s", out)
        return norm_real(out)
    except subprocess.CalledProcessError:
        # git returned error, we are not in a git repo
        return None
    except OSError:
        # git command not found, probably
        return None


def _git_ls_files_and_dirs(
    toplevel: str, *, timeout: int | None = None
) -> tuple[set[str], set[str]]:
    # Use git ls-files with -z for NUL-separated output (safe parsing).
    # --recurse-submodules lists files inside submodules with prefixed paths.
    # The exclude pathspec filters out files marked with the export-ignore
    # gitattribute, matching the old git-archive behavior.
    # "." is needed as positive pathspec for the exclude to apply against.
    # Uses run_git (--git-dir) to pin to the correct repository.
    res = run_git(
        [
            "ls-files",
            "-z",
            "--recurse-submodules",
            "--",
            ".",
            ":(exclude,attr:export-ignore)",
        ],
        Path(toplevel),
        timeout=timeout,
    )
    if res.returncode:
        log.error("listing git files failed - pretending there aren't any")
        return set(), set()

    git_files: set[str] = set()
    git_dirs: set[str] = {toplevel}
    for name in res.stdout.rstrip("\0").split("\0"):
        if not name:
            continue
        name = os.path.normcase(name).replace("/", os.path.sep)
        fullname = os.path.join(toplevel, name)
        git_files.add(fullname)
        dirname = os.path.dirname(fullname)
        while len(dirname) > len(toplevel) and dirname not in git_dirs:
            git_dirs.add(dirname)
            dirname = os.path.dirname(dirname)
    return git_files, git_dirs


def git_find_files(path: _t.PathT = "") -> list[str]:
    """Find files tracked in a Git repository"""
    toplevel = _git_toplevel(os.fspath(path))
    if not is_toplevel_acceptable(toplevel):
        return []
    fullpath = norm_real(path)
    if not fullpath.startswith(toplevel):
        log.warning("toplevel mismatch computed %s vs resolved %s ", toplevel, fullpath)
    git_files, git_dirs = _git_ls_files_and_dirs(toplevel)
    return scm_find_files(path, git_files, git_dirs)


def git_archive_find_files(path: _t.PathT = "") -> list[str]:
    """Find files in a Git archive (all files, since archive already filtered)"""
    # This function assumes that ``path`` is obtained from a git archive
    # and therefore all the files that should be ignored were already removed.
    archival = os.path.join(path, ".git_archival.txt")
    if not os.path.exists(archival):
        return []

    data = data_from_mime(archival)

    if "$Format" in data.get("node", ""):
        # Substitutions have not been performed, so not a reliable archive
        return []

    log.warning("git archive detected - fallback to listing all files")
    return scm_find_files(path, set(), set(), force_all_files=True)


__all__ = ["git_find_files", "git_archive_find_files"]
