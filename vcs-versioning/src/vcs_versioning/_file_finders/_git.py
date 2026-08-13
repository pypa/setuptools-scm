from __future__ import annotations

import logging
import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

from .. import _types as _t
from .._backends._git import run_git
from .._compat import norm_real, strip_path_suffix
from .._integration import data_from_mime
from .._run_cmd import run as _run
from . import collect_files_and_dirs, is_toplevel_acceptable, scm_find_files

log = logging.getLogger(__name__)

GITLINK_MODE = "160000"
"""index mode ``git ls-files -s`` reports for submodule entries"""


def _git_toplevel(path: str) -> str | None:
    try:
        cwd = os.path.abspath(path or ".")
        res = _run(["git", "rev-parse", "HEAD"], cwd=cwd)
        if res.returncode:
            # This catches you being in a git directory, but the
            # permissions being incorrect.  With modern containerized
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


def _ancestors(name: str) -> Iterator[str]:
    """Yield the directories a slash separated path is nested in."""
    index = name.find("/")
    while index != -1:
        yield name[:index]
        index = name.find("/", index + 1)


def _ls_files_entries(
    repo: Path, *, timeout: int | None = None
) -> list[tuple[str, str]] | None:
    """List tracked ``(mode, path)`` entries of *repo*.

    Uses NUL-separated output for safe parsing and ``-s`` to tell submodule
    entries (gitlinks) from ordinary files.  The exclude pathspec drops files
    carrying the ``export-ignore`` gitattribute - it matches per file, so
    directories and submodules are dealt with by the caller.
    ``None`` signals that git refused to list files (no repository yet,
    or a submodule that is not checked out).
    """
    res = run_git(
        ["ls-files", "-z", "-s", "--", ".", ":(exclude,attr:export-ignore)"],
        repo,
        timeout=timeout,
    )
    if res.returncode:
        return None
    entries = []
    for record in res.stdout.rstrip("\0").split("\0"):
        if not record:
            continue
        # <mode> SP <object> SP <stage> TAB <path>
        info, _, name = record.partition("\t")
        entries.append((info.split(" ", 1)[0], name))
    return entries


def _export_ignored_dirs(
    repo: Path, dirs: set[str], *, timeout: int | None = None
) -> set[str]:
    """Return the subset of *dirs* carrying the ``export-ignore`` attribute.

    ``git archive`` skips whole trees, but an ``export-ignore`` on a directory
    is not inherited by the paths below it, so the pathspec used for files
    cannot see it.  Directories are therefore queried explicitly, with the
    trailing slash git needs to match ``dir/`` style attribute patterns.
    """
    if not dirs:
        return set()
    res = run_git(
        ["check-attr", "-z", "--stdin", "export-ignore"],
        repo,
        timeout=timeout,
        input="\0".join(f"{name}/" for name in sorted(dirs)),
    )
    if res.returncode:
        log.warning("checking export-ignore attributes failed: %s", res.stderr)
        return set()
    # NUL separated <path> <attribute> <value> triples
    fields = res.stdout.split("\0")
    return {
        path.rstrip("/")
        for path, value in zip(fields[::3], fields[2::3])
        if value == "set"
    }


def _list_tracked_paths(repo: Path, *, timeout: int | None = None) -> list[str] | None:
    """Slash separated paths tracked in *repo*, submodules included.

    ``export-ignore`` is honored for files, directories and submodules,
    so a submodule below an ignored directory is skipped entirely instead
    of dragging its whole history into the distribution.
    """
    entries = _ls_files_entries(repo, timeout=timeout)
    if entries is None:
        return None
    candidates = {parent for _, name in entries for parent in _ancestors(name)}
    candidates.update(name for mode, name in entries if mode == GITLINK_MODE)
    ignored = _export_ignored_dirs(repo, candidates, timeout=timeout)

    paths: list[str] = []
    for mode, name in entries:
        if ignored and (
            name in ignored or any(parent in ignored for parent in _ancestors(name))
        ):
            log.debug("export-ignore excludes %s", name)
            continue
        if mode != GITLINK_MODE:
            paths.append(name)
            continue
        submodule = _list_tracked_paths(repo / name, timeout=timeout)
        if submodule is None:
            log.info("submodule %s is not checked out - not listing its files", name)
            continue
        paths.extend(f"{name}/{sub_name}" for sub_name in submodule)
    return paths


def _git_ls_files_and_dirs(
    toplevel: str, *, timeout: int | None = None
) -> tuple[set[str], set[str]]:
    # Uses run_git (--git-dir) to pin to the correct repository.
    paths = _list_tracked_paths(Path(toplevel), timeout=timeout)
    if paths is None:
        log.error("listing git files failed - pretending there aren't any")
        return set(), set()

    return collect_files_and_dirs(paths, norm_real(toplevel))


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


__all__ = ["git_archive_find_files", "git_find_files"]
