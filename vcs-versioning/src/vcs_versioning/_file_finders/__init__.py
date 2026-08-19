from __future__ import annotations

import logging
import os
import sys
import warnings
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path

if sys.version_info >= (3, 10):
    from typing import TypeGuard
else:
    from typing_extensions import TypeGuard

from .. import _types as _t
from .._compat import norm_real
from .._entrypoints import entry_points
from .._pyproject_reading import PyProjectData, read_pyproject
from .._toml import InvalidTomlError

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


def _pyproject_enables_scm(data: PyProjectData) -> bool:
    """Return True if *data* matches setuptools-scm's ``should_infer`` rules.

    Infer when an explicit ``[tool.setuptools_scm]`` / ``[tool.vcs-versioning]``
    section is present, or when ``setuptools-scm[simple]`` is in
    ``build-system.requires`` with ``version`` in ``project.dynamic``.
    """
    if data.section_present:
        return True
    if not data.project_present:
        return False
    if "version" not in data.project.get("dynamic", []):
        return False
    from .._requirement_cls import Requirement, extract_package_name

    for requirement_string in data.build_requires:
        try:
            requirement = Requirement(requirement_string)
            if (
                extract_package_name(requirement_string) == "setuptools-scm"
                and "simple" in requirement.extras
            ):
                return True
        except Exception:
            continue
    return False


def _project_configures_scm(path: _t.PathT) -> bool:
    """Return True if the project at *path* configures setuptools-scm."""
    root = Path(os.fspath(path) or ".").resolve()
    if not root.is_dir():
        root = root.parent

    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            data = read_pyproject(pyproject)
        except (OSError, InvalidTomlError):
            pass
        else:
            if _pyproject_enables_scm(data):
                return True

    setup_py = root / "setup.py"
    if setup_py.is_file():
        try:
            return "use_scm_version" in setup_py.read_text(encoding="utf-8")
        except OSError:
            return False
    return False


def _warn_if_file_finder_unconfigured(path: _t.PathT) -> None:
    """Warn when the file-finder entry point runs without setuptools-scm config.

    Library callers (and tests) that pass a bare VCS tree with no project
    metadata are left alone; setuptools always has ``pyproject.toml`` or
    ``setup.py`` when it invokes this entry point.
    """
    root = Path(os.fspath(path) or ".").resolve()
    if not root.is_dir():
        root = root.parent
    if not (root / "pyproject.toml").is_file() and not (root / "setup.py").is_file():
        return
    if _project_configures_scm(path):
        return
    warnings.warn(
        "The setuptools.file_finders entry point is deprecated and will be "
        "removed in a future major release. Configure setuptools-scm via "
        "[tool.setuptools_scm] in pyproject.toml or use_scm_version in "
        "setup.py; file inclusion will then use the workdir API instead.",
        DeprecationWarning,
        stacklevel=3,
    )


def find_files(path: _t.PathT = "") -> list[str]:
    """Discover files using registered file finder entry points.

    Invoking this via the ``setuptools.file_finders`` entry point without
    configuring setuptools-scm is deprecated and will be removed in a
    future major release.
    """
    eps = [
        *entry_points(group="setuptools_scm.files_command"),
        *entry_points(group="setuptools_scm.files_command_fallback"),
    ]
    result: list[str] = []
    for ep in eps:
        command: Callable[[_t.PathT], list[str]] = ep.load()
        res: list[str] = command(path)
        if res:
            result = res
            break

    _warn_if_file_finder_unconfigured(path)
    return result


def collect_files_and_dirs(
    raw_names: Iterable[str], toplevel: str
) -> tuple[set[str], set[str]]:
    """Normalize VCS file listings into absolute ``(files, dirs)`` sets.

    Each backend produces a list of relative paths from its own command
    (``git ls-files``, ``hg files``, ``jj file list``).  This helper
    normalizes case and separators, joins with *toplevel*, and collects
    the directory ancestry — the same loop that was previously duplicated
    in every backend.
    """
    files: set[str] = set()
    dirs: set[str] = {toplevel}
    for name in raw_names:
        if not name:
            continue
        name = os.path.normcase(name).replace("/", os.path.sep)
        fullname = os.path.join(toplevel, name)
        files.add(fullname)
        dirname = os.path.dirname(fullname)
        while len(dirname) > len(toplevel) and dirname not in dirs:
            dirs.add(dirname)
            dirname = os.path.dirname(dirname)
    return files, dirs


__all__ = [
    "collect_files_and_dirs",
    "find_files",
    "is_toplevel_acceptable",
    "scm_find_files",
]
