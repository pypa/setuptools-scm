from __future__ import annotations

import dataclasses
import fnmatch
import logging
import os
import re
import shlex
import sys
import warnings
from collections.abc import Callable, Sequence
from datetime import date, datetime, timezone
from enum import Enum
from os.path import samefile
from pathlib import Path
from subprocess import CalledProcessError
from typing import TYPE_CHECKING, ClassVar

from .. import _discover as discover
from .. import _types as _t
from .._config import Configuration
from .._integration import data_from_mime
from .._run_cmd import CompletedProcess as _CompletedProcess
from .._run_cmd import require_command as _require_command
from .._run_cmd import run as _run
from .._scm_version import ScmVersion, meta, tag_to_version
from ._scm_workdir import (
    STRICT_DIAGNOSTIC,
    Workdir,
    config_location,
    get_latest_file_mtime,
    report_once,
    version_outcome,
)

if TYPE_CHECKING:
    from .._protocols import DistanceScopeCapable, GitQueryable
    from . import _hg_git as hg_git
log = logging.getLogger(__name__)

REF_TAG_RE = re.compile(r"(?<=\btag: )([^,]+)\b")
DESCRIBE_UNSUPPORTED = "%(describe"

# ``git describe`` appends ``-<distance>-g<abbreviated node>`` to the tag name.
# Tags may contain dashes themselves, so the suffix has to be matched precisely
# instead of just splitting on the last two dashes.
DESCRIBE_SUFFIX_RE = re.compile(r"^(?P<tag>.+)-(?P<distance>\d+)-g(?P<node>[0-9a-f]+)$")


# If testing command in shell make sure to quote the match argument like
# '*[0-9]*' as it will expand before being sent to git if there are any matching
# files in current directory.
def make_describe_command(match: str) -> list[str]:
    """Build a ``git describe`` command list restricted to tags matching *match*."""
    return [
        "git",
        "describe",
        "--dirty",
        "--tags",
        "--long",
        "--abbrev=40",
        "--match",
        match,
    ]


DEFAULT_DESCRIBE = make_describe_command("*[0-9]*")


class GitDistanceCount(Enum):
    """How commits are counted when ``scm.git.distance_scope`` restricts them.

    Both policies are set predicates over the commits reachable from ``HEAD``
    but not from the tag, so the count never decreases as history advances --
    the property a version number depends on.  Git's default history
    simplification is deliberately not offered: it is a traversal rule rather
    than a predicate and can make the distance *shrink* across a merge.
    """

    FULL_HISTORY = "full-history"
    """Every commit whose content at the scoped paths differs from a parent."""

    FIRST_PARENT = "first-parent"
    """The same, restricted to the first-parent chain (mainline changes only)."""


_DISTANCE_COUNT_FLAGS: dict[GitDistanceCount, str] = {
    GitDistanceCount.FULL_HISTORY: "--full-history",
    GitDistanceCount.FIRST_PARENT: "--first-parent",
}


class GitPreParse(Enum):
    """Available git pre-parse functions"""

    WARN_ON_SHALLOW = "warn_on_shallow"
    FAIL_ON_SHALLOW = "fail_on_shallow"
    FETCH_ON_SHALLOW = "fetch_on_shallow"
    FAIL_ON_MISSING_SUBMODULES = "fail_on_missing_submodules"


def run_git(
    args: Sequence[str | os.PathLike[str]],
    repo: Path,
    *,
    check: bool = False,
    timeout: int | None = None,
    input: str | None = None,
) -> _CompletedProcess:
    return _run(
        ["git", "--git-dir", repo / ".git", *args],
        cwd=repo,
        check=check,
        timeout=timeout,
        input=input,
    )


class GitWorkdir(Workdir):
    """experimental, may change at any time"""

    supports_distance_scope: ClassVar[bool] = True
    """Whether ``scm.git.distance_scope`` can be honoured for this workdir.

    ``GitWorkdirHgClient`` inherits from this class but emulates ``describe``
    through mercurial and has no usable ``run_git``, so it must opt out rather
    than silently count zero commits.
    """

    def run_git(
        self,
        args: Sequence[str | os.PathLike[str]],
        *,
        check: bool = False,
        timeout: int | None = None,
    ) -> _CompletedProcess:
        return run_git(
            args, self.path, check=check, timeout=timeout or self._subprocess_timeout
        )

    @classmethod
    def from_potential_worktree(
        cls, wd: _t.PathT, config: Configuration | None = None
    ) -> GitWorkdir | None:
        wd = Path(wd).resolve()
        timeout = config.env.subprocess_timeout if config is not None else None
        real_wd = run_git(
            ["rev-parse", "--show-prefix"], wd, timeout=timeout
        ).parse_success(parse=str)
        if real_wd is None:
            return None
        else:
            real_wd = real_wd[:-1]  # remove the trailing pathsep

        if not real_wd:
            real_wd = os.fspath(wd)
        else:
            str_wd = os.fspath(wd)
            from .._compat import strip_path_suffix

            real_wd = strip_path_suffix(str_wd, real_wd)
        log.debug("real root %s", real_wd)
        if not samefile(real_wd, wd):
            return None

        result = cls(Path(real_wd))
        result._config = config
        return result

    def is_dirty(self) -> bool:
        return self.run_git(
            ["status", "--porcelain", "--untracked-files=no"],
        ).parse_success(
            parse=bool,
            default=False,
        )

    def get_branch(self) -> str | None:
        return self.run_git(
            ["rev-parse", "--abbrev-ref", "HEAD"],
        ).parse_success(
            parse=str,
            error_msg="branch err (abbrev-err)",
        ) or self.run_git(
            ["symbolic-ref", "--short", "HEAD"],
        ).parse_success(
            parse=str,
            error_msg="branch err (symbolic-ref)",
        )

    def get_head_date(self) -> date | None:
        def parse_timestamp(timestamp_text: str) -> date | None:
            if "%c" in timestamp_text:
                log.warning("git too old -> timestamp is %r", timestamp_text)
                return None
            if sys.version_info < (3, 11) and timestamp_text.endswith("Z"):
                timestamp_text = timestamp_text[:-1] + "+00:00"

            # Convert to UTC to ensure consistent date regardless of local timezone
            dt = datetime.fromisoformat(timestamp_text)
            log.debug("dt: %s", dt)
            dt_utc = dt.astimezone(timezone.utc).date()
            log.debug("dt utc: %s", dt_utc)
            return dt_utc

        res = self.run_git(
            [
                *("-c", "log.showSignature=false"),
                *("log", "-n", "1", "HEAD"),
                "--format=%cI",
            ],
        )
        return res.parse_success(
            parse=parse_timestamp,
            error_msg="logging the iso date for head failed",
        )

    def get_dirty_tag_date(self) -> date | None:
        """Get the latest modification time of changed files in the working directory.

        Returns the date of the most recently modified file that has changes,
        or None if no files are changed or if an error occurs.
        """
        if not self.is_dirty():
            return None

        try:
            # Get list of changed files
            changed_files_res = self.run_git(
                ["diff", "--name-only"],
            )
            if changed_files_res.returncode != 0:
                return None

            changed_files = changed_files_res.stdout.strip().split("\n")
            return get_latest_file_mtime(changed_files, self.path)

        except Exception as e:
            log.debug("Failed to get dirty tag date: %s", e)
            return None

    def is_shallow(self) -> bool:
        return self.path.joinpath(".git/shallow").is_file()

    def head_is_exact_tag(self) -> bool:
        """True when HEAD points exactly at a tag (including lightweight tags)."""
        res = self.run_git(
            ["describe", "--exact-match", "--tags", "HEAD"],
        )
        return res.returncode == 0

    def fetch_shallow(self) -> None:
        try:
            self.run_git(
                ["fetch", "--unshallow", "--filter=blob:none"],
                check=True,
                timeout=240,
            )
        except CalledProcessError:
            self.run_git(["fetch", "--unshallow"], check=True, timeout=240)

    def node(self) -> str | None:
        return self.run_git(
            ["rev-parse", "--verify", "--quiet", "HEAD"],
        ).parse_success(
            parse=str,
        )

    def count_all_nodes(self) -> int:
        res = self.run_git(["rev-list", "HEAD"])
        return res.stdout.count("\n") + 1

    def count_nodes_in_scope(self, paths: Sequence[str], since: str | None) -> int:
        """Count commits touching *paths*, optionally only after *since*.

        *since* is the raw tag name as ``git describe`` reported it, so it is
        passed to ``rev-list`` verbatim.  ``None`` counts from the root.
        """
        flag = _DISTANCE_COUNT_FLAGS[self.config.scm.git.distance_count]
        revs = f"{since}..HEAD" if since is not None else "HEAD"
        res = self.run_git(["rev-list", "--count", flag, revs, "--", *paths])
        return res.parse_success(parse=int, default=0, error_msg="scoped rev-list")

    def is_dirty_in_scope(self, paths: Sequence[str]) -> bool:
        return self.run_git(
            ["status", "--porcelain", "--untracked-files=no", "--", *paths],
        ).parse_success(
            parse=bool,
            default=False,
        )

    def tag_namespaces(self, match_glob: str) -> set[str]:
        """Leading namespaces of the tags reachable from HEAD matching *glob*.

        ``pkg-a/v1.2`` and ``pkg-b/v3.0`` yield ``{"pkg-a/", "pkg-b/"}``; a
        repository tagged ``v1.2``, ``v1.3`` yields ``{""}``.  Used to detect
        per-project tagging schemes where an unfiltered ``git describe`` would
        pick a *sibling* project's tag.
        """
        res = self.run_git(["tag", "--merged", "HEAD", "--list", match_glob])
        prefix = self.config.tag.prefix
        namespaces = set()
        for line in res.stdout.splitlines():
            tag = line.strip()
            if not tag:
                continue
            if prefix and tag.startswith(prefix):
                tag = tag[len(prefix) :]
            match = re.search(r"\d", tag)
            namespaces.add(tag[: match.start()] if match else tag)
        return namespaces

    def default_describe(self) -> _CompletedProcess:
        match_glob = self.config.tag.describe_match_glob()
        cmd = make_describe_command(match_glob)
        res = self.run_git(cmd[1:])
        if self.config.tag.strict is None:
            _warn_if_strict_would_differ(self, self.config, res)
        return res

    def get_scm_version(self) -> ScmVersion | None:
        """Obtain version metadata from this git work directory."""
        config = self.config
        effective_pre_parse = _GIT_PRE_PARSE_FUNCTIONS.get(
            config.scm.git.pre_parse, warn_on_shallow
        )
        return _git_parse_inner(config, self, pre_parse=effective_pre_parse)

    def list_tracked_files(self, path: Path | str = "") -> list[str]:
        """List files tracked by git, honoring export-ignore.

        When no path is given, scopes to ``project_root`` (not the VCS root)
        so that monorepo projects only list their own files.
        """
        from .._file_finders import scm_find_files
        from .._file_finders._git import _git_ls_files_and_dirs

        base = str(path) if path else str(self.project_root)
        git_files, git_dirs = _git_ls_files_and_dirs(
            str(self.path), timeout=self._subprocess_timeout
        )
        return sorted(scm_find_files(base, git_files, git_dirs))

    def is_file_tracked(self, path: Path) -> bool:
        res = self.run_git(
            ["ls-files", "--error-unmatch", str(path)],
        )
        return res.returncode == 0


def _describe_tag(output: str) -> str | None:
    """Extract just the tag name from a ``git describe --long`` output."""
    if not output.strip():
        return None
    return _git_parse_describe(output.strip())[0]


def _strict_match_glob(prefix: str) -> str:
    """The ``--match`` glob ``tag.strict = true`` would produce."""
    return f"{prefix}*[0-9]*.*[0-9]*"


def _describe_outcome(output: str, config: Configuration) -> str:
    """Render what a ``git describe`` *output* would yield as a version."""
    if not output.strip():
        return version_outcome(config, None)

    tag, distance, node, dirty = _git_parse_describe(output.strip())
    return version_outcome(config, tag, distance=distance, dirty=dirty, node=node)


def _warn_if_strict_would_differ(
    wd: GitQueryable, config: Configuration, permissive: _CompletedProcess
) -> None:
    """Report the ``tag.strict`` future default only when it changes the answer.

    ``tag.strict`` is unset, so the permissive glob was used.  Stay silent
    unless the strict glob would pick a different tag, so that projects the
    future default cannot affect are never nagged.
    """
    permissive_tag = _describe_tag(permissive.stdout)
    strict_glob = _strict_match_glob(config.tag.prefix)

    if permissive_tag is None:
        # nothing matched the wider glob, so nothing matches the narrower one
        return
    if fnmatch.fnmatchcase(permissive_tag, strict_glob):
        # the strict glob matches a subset of the permissive one, so a
        # permissive answer that is itself strict-matching is also the
        # closest strict-matching tag -- no subprocess needed
        return

    strict = wd.run_git(make_describe_command(strict_glob)[1:])
    report_once(
        f"strict-divergence:{wd.path}:{permissive_tag}:{_describe_tag(strict.stdout)}",
        STRICT_DIAGNOSTIC,
        _describe_outcome(permissive.stdout, config),
        _describe_outcome(strict.stdout, config),
        config_location(config),
    )


def _warn_if_describe_command_overrides_strict(
    wd: GitQueryable, config: Configuration, describe_res: _CompletedProcess
) -> None:
    """Report that ``describe_command`` beat an explicit ``tag.strict``.

    Only fires when the two actually disagree about which tag to use --
    setting both is harmless as long as they pick the same tag.  ``tag.prefix``
    is deliberately not mentioned: it still strips the prefix before version
    parsing, so combining it with ``describe_command`` is legitimate.
    """
    strict_glob = _strict_match_glob(config.tag.prefix)
    strict = wd.run_git(make_describe_command(strict_glob)[1:])
    strict_tag = _describe_tag(strict.stdout)
    describe_tag = _describe_tag(describe_res.stdout)
    if strict_tag == describe_tag:
        return

    report_once(
        f"describe-overrides-strict:{wd.path}:{describe_tag}:{strict_tag}",
        "scm.git.describe_command takes precedence over tag.strict, and they"
        " disagree for this repository:\n"
        "  describe_command gives:      %s\n"
        "  tag.strict = %s would give: %s\n"
        "Drop tag.strict, or drop describe_command and let tag.prefix/tag.strict"
        " build the match pattern, in %s.",
        _describe_outcome(describe_res.stdout, config),
        str(config.tag.strict).lower(),
        _describe_outcome(strict.stdout, config),
        config_location(config),
    )


def warn_on_shallow(wd: GitWorkdir) -> None:
    """experimental, may change at any time"""
    if wd.is_shallow() and not wd.head_is_exact_tag():
        warnings.warn(f'"{wd.path}" is shallow and may cause errors', stacklevel=2)


def fetch_on_shallow(wd: GitWorkdir) -> None:
    """experimental, may change at any time"""
    if wd.is_shallow() and not wd.head_is_exact_tag():
        warnings.warn(
            f'"{wd.path}" was shallow, git fetch was used to rectify', stacklevel=2
        )
        wd.fetch_shallow()


def fail_on_shallow(wd: GitWorkdir) -> None:
    """experimental, may change at any time"""
    if wd.is_shallow() and not wd.head_is_exact_tag():
        raise ValueError(
            f'{wd.path} is shallow, please correct with "git fetch --unshallow"'
        )


def fail_on_missing_submodules(wd: GitWorkdir) -> None:
    """
    Fail if submodules are defined but not initialized/cloned.

    This pre_parse function checks if there are submodules defined in .gitmodules
    but not properly initialized (cloned). This helps prevent packaging incomplete
    projects when submodules are required for a complete build.
    """
    gitmodules_path = wd.path / ".gitmodules"
    if not gitmodules_path.exists():
        # No submodules defined, nothing to check
        return

    # Get submodule status - lines starting with '-' indicate uninitialized submodules
    status_result = wd.run_git(["submodule", "status"])
    if status_result.returncode != 0:
        # Command failed, might not be in a git repo or other error
        log.debug("Failed to check submodule status: %s", status_result.stderr)
        return

    status_lines = (
        status_result.stdout.strip().split("\n") if status_result.stdout.strip() else []
    )
    uninitialized_submodules = []

    for line in status_lines:
        line = line.strip()
        if line.startswith("-"):
            # Extract submodule path (everything after the commit hash)
            parts = line.split()
            if len(parts) >= 2:
                submodule_path = parts[1]
                uninitialized_submodules.append(submodule_path)

    # If .gitmodules exists but git submodule status returns nothing,
    # it means submodules are defined but not properly set up (common after cloning without --recurse-submodules)
    if not status_lines and gitmodules_path.exists():
        raise ValueError(
            f"Submodules are defined in .gitmodules but not initialized in {wd.path}. "
            f"Please run 'git submodule update --init --recursive' to initialize them."
        )

    if uninitialized_submodules:
        submodule_list = ", ".join(uninitialized_submodules)
        raise ValueError(
            f"Submodules are not initialized in {wd.path}: {submodule_list}. "
            f"Please run 'git submodule update --init --recursive' to initialize them."
        )


# Mapping from enum items to actual pre_parse functions
_GIT_PRE_PARSE_FUNCTIONS: dict[GitPreParse, Callable[[GitWorkdir], None]] = {
    GitPreParse.WARN_ON_SHALLOW: warn_on_shallow,
    GitPreParse.FAIL_ON_SHALLOW: fail_on_shallow,
    GitPreParse.FETCH_ON_SHALLOW: fetch_on_shallow,
    GitPreParse.FAIL_ON_MISSING_SUBMODULES: fail_on_missing_submodules,
}


def get_working_directory(config: Configuration, root: _t.PathT) -> GitWorkdir | None:
    """
    Return the working directory (``GitWorkdir``).
    """

    if config.parent:  # todo broken
        return GitWorkdir.from_potential_worktree(config.parent, config)

    for potential_root in discover.walk_potential_roots(
        root, search_parents=config.search_parent_directories
    ):
        potential_wd = GitWorkdir.from_potential_worktree(potential_root, config)
        if potential_wd is not None:
            return potential_wd

    return GitWorkdir.from_potential_worktree(root, config)


def parse(
    root: _t.PathT,
    config: Configuration,
    describe_command: str | list[str] | None = None,
    pre_parse: Callable[[GitWorkdir], None] | None = None,
) -> ScmVersion | None:
    """
    :param pre_parse: experimental pre_parse action, may change at any time.
                     Takes precedence over config.git_pre_parse if provided.
    """
    _require_command("git")
    wd = get_working_directory(config, root)
    if wd:
        # Use function parameter first, then config setting, then default
        if pre_parse is not None:
            effective_pre_parse = pre_parse
        else:
            # config.scm.git.pre_parse is always a GitPreParse enum instance
            effective_pre_parse = _GIT_PRE_PARSE_FUNCTIONS.get(
                config.scm.git.pre_parse, warn_on_shallow
            )

        return _git_parse_inner(
            config, wd, describe_command=describe_command, pre_parse=effective_pre_parse
        )
    else:
        return None


SCOPE_NAMESPACE_DIAGNOSTIC = (
    "scm.git.distance_scope is enabled, but the tags reachable from HEAD span"
    " several project namespaces (%s).\n"
    "git describe picks the topologically nearest tag, which may well belong to"
    " a *different* project, and the distance would then be counted from that"
    " project's release.\n"
    "Set tag.prefix (or scm.git.describe_command) so only this project's tags"
    " are considered, in %s."
)


def resolve_scope_paths(
    wd: DistanceScopeCapable, config: Configuration
) -> list[str] | None:
    """Paths the distance count is restricted to, or ``None`` when disabled.

    The project's own directory always participates; ``distance_scope`` may add
    further directories (shared libraries, tooling) whose commits should also
    move this project's version.
    """
    extra = config.scm.git.scope_paths
    if extra is None:
        return None

    if not wd.supports_distance_scope:
        raise ValueError(
            "scm.git.distance_scope is not supported for"
            f" {type(wd).__name__} at {wd.path}; it is a git-only feature."
        )

    project_path = wd.project_path
    if not project_path:
        raise ValueError(
            "scm.git.distance_scope is set, but the project directory is the VCS"
            f" root ({wd.path}), so restricting the count to it would be a no-op."
            " Set root/relative_to so the project is below the VCS root, or drop"
            " distance_scope."
        )
    return [project_path, *extra]


def _warn_if_tags_span_namespaces(
    wd: DistanceScopeCapable, config: Configuration
) -> None:
    """Report per-project tags that ``git describe`` may cross (:issue:`1056`).

    Counting a distance from a sibling project's tag is silently wrong, and the
    only cheap signal is that the reachable tags carry more than one namespace.
    A single namespace -- one global release train, or tag.prefix already
    narrowing to this project -- stays quiet.
    """
    namespaces = wd.tag_namespaces(config.tag.describe_match_glob())
    if len(namespaces) < 2:
        return
    report_once(
        f"scope-tag-namespaces:{wd.path}:{sorted(namespaces)}",
        SCOPE_NAMESPACE_DIAGNOSTIC,
        ", ".join(repr(ns) for ns in sorted(namespaces)),
        config_location(config),
    )


def apply_distance_scope(
    wd: DistanceScopeCapable,
    config: Configuration,
    tag: str,
    distance: int,
    dirty: bool,
) -> tuple[int, bool]:
    """Recount *distance* and *dirty* over the configured scope paths.

    *tag* is the raw ref name as ``git describe`` reported it -- ``meta()`` has
    not parsed it yet, which is why this runs here and not on the finished
    ``ScmVersion``.
    """
    paths = resolve_scope_paths(wd, config)
    if paths is None:
        return distance, dirty

    _warn_if_tags_span_namespaces(wd, config)
    scoped = wd.count_nodes_in_scope(paths, since=tag)
    log.debug("distance %s -> %s scoped to %s", distance, scoped, paths)
    return scoped, wd.is_dirty_in_scope(paths)


def _fail_on_shallow_scope(wd: DistanceScopeCapable, config: Configuration) -> None:
    """A shallow clone cannot answer a path-restricted count.

    ``warn_on_shallow`` is enough for a repository-wide distance, which merely
    ends up too small.  A scoped count walks history looking for commits that
    touch the paths, so a truncated history does not just shorten the answer --
    it can miss every relevant commit and report zero, which reads as an exact
    tag.
    """
    if config.scm.git.scope_paths is None:
        return
    if wd.is_shallow() and not wd.head_is_exact_tag():
        raise ValueError(
            f"{wd.path} is shallow and scm.git.distance_scope is enabled;"
            ' the path-restricted distance would be wrong. Correct with "git'
            ' fetch --unshallow", or drop distance_scope.'
        )


def version_from_describe(
    wd: DistanceScopeCapable,
    config: Configuration,
    describe_command: _t.CMD_TYPE | None,
) -> ScmVersion | None:
    if config.scm.git.describe_command is not None:
        describe_command = config.scm.git.describe_command

    if describe_command is not None:
        if isinstance(describe_command, str):
            describe_command = shlex.split(describe_command)
            # todo: figure how to ensure git with gitdir gets correctly invoked
        cmd_args = [str(a) for a in describe_command]
        if cmd_args[0] == "git":
            describe_res = wd.run_git(cmd_args[1:])
        else:
            describe_res = _run(cmd_args, wd.path, timeout=wd._subprocess_timeout)
        if config.tag.strict is not None:
            _warn_if_describe_command_overrides_strict(wd, config, describe_res)
    else:
        describe_res = wd.default_describe()

    def parse_describe(output: str) -> ScmVersion:
        tag, distance, node, dirty = _git_parse_describe(output)
        distance, dirty = apply_distance_scope(wd, config, tag, distance, dirty)
        return meta(tag=tag, distance=distance, dirty=dirty, node=node, config=config)

    return describe_res.parse_success(parse=parse_describe)


def _git_parse_inner(
    config: Configuration,
    wd: GitWorkdir | hg_git.GitWorkdirHgClient,
    pre_parse: Callable[[GitWorkdir | hg_git.GitWorkdirHgClient], None] | None = None,
    describe_command: _t.CMD_TYPE | None = None,
) -> ScmVersion:
    # wd satisfies both DescribeCapable and WorkdirState protocols.
    # The scope guard runs first: it is a hard error, and warn_on_shallow would
    # otherwise report the same shallow clone as a mere warning.
    _fail_on_shallow_scope(wd, config)
    if pre_parse:
        pre_parse(wd)

    version = version_from_describe(wd, config, describe_command)

    if version is None:
        # If 'git git_describe_command' failed, try to get the information otherwise.
        tag = config.version_cls(config.fallback_version or "0.0")
        node = wd.node()
        if node is None:
            distance = 0
            dirty = True
        else:
            scope_paths = resolve_scope_paths(wd, config)
            if scope_paths is None:
                distance = wd.count_all_nodes()
                dirty = wd.is_dirty()
            else:
                # No tag at all, so count this project's whole history.
                distance = wd.count_nodes_in_scope(scope_paths, since=None)
                dirty = wd.is_dirty_in_scope(scope_paths)
            node = "g" + node
        version = meta(
            tag=tag, distance=distance, dirty=dirty, node=node, config=config
        )
    branch = wd.get_branch()
    node_date = wd.get_head_date()

    # If we can't get node_date from HEAD (e.g., no commits yet),
    # and the working directory is dirty, try to use the latest
    # modification time of changed files instead of current time
    if node_date is None and wd.is_dirty():
        dirty_date = wd.get_dirty_tag_date()
        if dirty_date is not None:
            node_date = dirty_date

    # Final fallback to current time
    if node_date is None:
        node_date = datetime.now(timezone.utc).date()

    return dataclasses.replace(version, branch=branch, node_date=node_date)


def _git_parse_describe(
    describe_output: str,
) -> tuple[str, int, str | None, bool]:
    # 'describe_output' looks e.g. like 'v1.5.0-0-g4060507' or
    # 'v1.15.1rc1-37-g9bd1298-dirty'.
    # It may also just be a bare tag name if this is a tagged commit and we are
    # parsing a .git_archival.txt file.

    if describe_output.endswith("-dirty"):
        dirty = True
        describe_output = describe_output[:-6]
    else:
        dirty = False

    match = DESCRIBE_SUFFIX_RE.match(describe_output)
    if match is None:  # probably a tagged commit
        return describe_output, 0, None, dirty
    return (
        match.group("tag"),
        int(match.group("distance")),
        "g" + match.group("node"),
        dirty,
    )


def archival_to_version(
    data: dict[str, str], config: Configuration
) -> ScmVersion | None:
    node: str | None
    log.debug("data %s", data)
    archival_describe = data.get("describe-name", DESCRIBE_UNSUPPORTED)
    if DESCRIBE_UNSUPPORTED in archival_describe:
        warnings.warn("git archive did not support describe output", stacklevel=2)
    elif not archival_describe:
        log.debug("describe-name is empty (no tags in repo), falling through")
    else:
        tag, number, node, _ = _git_parse_describe(archival_describe)
        number = _archival_distance(number, config)
        return meta(
            tag,
            config=config,
            distance=number,
            node=node,
        )

    for ref in REF_TAG_RE.findall(data.get("ref-names", "")):
        version = tag_to_version(ref, config)
        if version is not None:
            return meta(version, config=config)
    node = data.get("node")
    if node is None:
        return None
    elif "$FORMAT" in node.upper():
        warnings.warn(
            "unprocessed git archival found (no export subst applied)", stacklevel=2
        )
        return None
    else:
        return meta("0.0", node=node, config=config)


ARCHIVAL_SCOPE_DIAGNOSTIC = (
    "scm.git.distance_scope is enabled, but this build reads its version from a"
    " git archive, whose describe output git can only record for the whole"
    " repository -- ``%%(describe)`` takes no pathspec.\n"
    "The distance %s is therefore an upper bound on the %d commit(s) that"
    " actually touched this project, and the version comes out too high.\n"
    "Build from an sdist (which carries the already-computed version) or from a"
    " checkout for an exact number."
)


def _archival_distance(number: int, config: Configuration) -> int:
    """Report that an archive's distance overshoots the scoped one (:issue:`1056`).

    An archive of a *tag* has distance 0, and a scoped count of a zero-commit
    range is also 0 -- the common release-tarball case is exact and stays
    silent.  Beyond that the recorded count is repository-wide and can only be
    too large, never too small, so the value is still usable; it just is not
    the number the configuration asked for.
    """
    if number == 0 or config.scm.git.scope_paths is None:
        return number
    report_once(
        f"archival-scope-overshoot:{number}",
        ARCHIVAL_SCOPE_DIAGNOSTIC,
        number,
        number,
    )
    return number


def parse_archival(root: _t.PathT, config: Configuration) -> ScmVersion | None:
    archival = os.path.join(root, ".git_archival.txt")
    data = data_from_mime(archival)
    return archival_to_version(data, config=config)
