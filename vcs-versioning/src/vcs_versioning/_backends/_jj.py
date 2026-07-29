"""Jujutsu (jj) VCS backend.

Provides version inference from Jujutsu repositories using native ``jj``
commands.  Jujutsu uses Git as its storage backend but maintains its own
commit graph, tags, and bookmarks (branches).

Key differences from Git that this module accounts for:

* The working-copy commit (``@``) is always present and may be empty.
  The "real" HEAD is typically ``@-`` or the latest non-empty ancestor.
* There is no staging area -- all working-copy changes are part of ``@``.
* Branches are called "bookmarks" in jj.
* Tags are native as of jj 0.42+.
"""

from __future__ import annotations

import dataclasses
import logging
import os
from collections.abc import Sequence
from datetime import date, datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from .. import _types as _t
from .._run_cmd import CompletedProcess as _CompletedProcess
from .._run_cmd import require_command as _require_command
from .._run_cmd import run as _run
from .._scm_version import ScmVersion, meta
from ._scm_workdir import Workdir

if TYPE_CHECKING:
    from .._config import Configuration

log = logging.getLogger(__name__)

ANCESTOR_SCAN_LIMIT = 20
"""Generations of ancestors examined when looking for the newest real commit.

Revsets filtered by ``empty()`` force jj to diff every candidate commit
against its parents, so applying such a filter to the full ancestry costs
O(history) and takes minutes in large repositories (issue #1477).  Empty
commits only occur near the head in practice -- ``@`` itself, plus the
occasional ``jj new`` chain -- so a small window suffices.
"""


def run_jj(
    args: Sequence[str | os.PathLike[str]],
    repo: Path,
    *,
    check: bool = False,
    timeout: int | None = None,
    ignore_working_copy: bool = False,
) -> _CompletedProcess:
    cmd: list[str | os.PathLike[str]] = ["jj", "--no-pager", "--repository", str(repo)]
    if ignore_working_copy:
        cmd.append("--ignore-working-copy")
    cmd.extend(args)
    return _run(cmd, cwd=repo, check=check, timeout=timeout)


class JjWorkdir(Workdir):
    """Work directory backed by Jujutsu (jj)."""

    _snapshot_taken: bool = False
    """Whether a command in this process refreshed the working-copy commit."""

    def run_jj(
        self,
        args: Sequence[str | os.PathLike[str]],
        *,
        check: bool = False,
        timeout: int | None = None,
        needs_snapshot: bool = False,
    ) -> _CompletedProcess:
        """Run a jj command in this work directory.

        jj snapshots the working copy on every invocation, which scans the
        whole tree and writes an operation-log entry.  One snapshot per
        process is enough, so history queries following it pass
        ``--ignore-working-copy``.  Commands that must observe uncommitted
        edits set ``needs_snapshot``.
        """
        ignore_working_copy = self._snapshot_taken and not needs_snapshot
        self._snapshot_taken = True
        return run_jj(
            args,
            self.path,
            check=check,
            timeout=timeout or self._subprocess_timeout,
            ignore_working_copy=ignore_working_copy,
        )

    @classmethod
    def from_potential_worktree(
        cls, wd: Path, config: Configuration | None = None
    ) -> JjWorkdir | None:
        wd = Path(wd).resolve()
        if not (wd / ".jj").is_dir():
            return None

        timeout = config.env.subprocess_timeout if config is not None else None
        res = run_jj(["root"], wd, timeout=timeout, ignore_working_copy=True)
        root = res.parse_success(parse=str)
        if root is None:
            return None

        result = cls(Path(root))
        result._config = config
        return result

    def is_dirty(self) -> bool:
        res = self.run_jj(["diff", "--summary"], needs_snapshot=True)
        return res.parse_success(parse=bool, default=False)

    def get_branch(self) -> str | None:
        """Return the first local bookmark on the working copy's parent.

        In jj, ``@`` is the (potentially empty) working-copy commit.
        Bookmarks are normally set on ``@-``, the parent that was created
        by ``jj commit``.  We also check ``@`` as a fallback in case the
        user placed a bookmark directly on the working copy.
        """
        for rev in ("@-", "@"):
            res = self.run_jj(
                [
                    "log",
                    "--no-graph",
                    "-r",
                    rev,
                    "-T",
                    'local_bookmarks.map(|b| b.name()).join(",")',
                ],
            )
            branch = res.parse_success(parse=str)
            if branch:
                return branch
        return None

    def get_head_date(self) -> date | None:
        def parse_timestamp(text: str) -> date | None:
            if not text:
                return None
            dt = datetime.fromisoformat(text)
            return dt.astimezone(timezone.utc).date()

        res = self.run_jj(
            [
                "log",
                "--no-graph",
                "-r",
                "@",
                "-T",
                'committer.timestamp().utc().format("%Y-%m-%dT%H:%M:%S%:z")',
            ],
        )
        return res.parse_success(
            parse=parse_timestamp,
            error_msg="failed to get jj head date",
        )

    def _count_revset(self, revset: str) -> int:
        """Count the commits a revset resolves to."""
        res = self.run_jj(["log", "--no-graph", "-r", revset, "-T", '"x\\n"'])
        output = res.parse_success(parse=str)
        if not output:
            return 0
        return output.count("\n") + 1

    def node(self) -> str | None:
        """Return the newest ancestor of ``@`` that is a real commit.

        This is jj's equivalent of git's ``HEAD``: the working-copy commit
        ``@`` is skipped while it holds no changes, as are the empty
        commits a ``jj new`` chain leaves behind.  Merges and tagged
        commits are kept even when empty -- git counts them too.

        Only ``ANCESTOR_SCAN_LIMIT`` generations are examined; the
        unbounded query remains as a fallback for histories that are
        empty all the way down.
        """
        skip = "empty() ~ tags() ~ merges()"
        revsets = [
            f"latest(ancestors(@, {ANCESTOR_SCAN_LIMIT}) ~ ({skip}))",
            f"latest(::@ ~ ({skip}))",
        ]
        for revset in revsets:
            res = self.run_jj(["log", "--no-graph", "-r", revset, "-T", "commit_id"])
            result = res.parse_success(parse=str)
            if result:
                return result
            log.debug("no non-empty commit found in %s", revset)
        return None

    def _find_latest_tag(self) -> str | None:
        """Find the tag of the latest tagged ancestor of the working copy."""
        res = self.run_jj(
            [
                "log",
                "--no-graph",
                "-r",
                "latest(heads(::@ & tags()))",
                "-T",
                'tags.map(|t| t.name()).join(",")',
            ],
        )
        tag_names = res.parse_success(parse=str)
        if not tag_names:
            return None

        # Take the first tag if multiple point at the same commit
        return tag_names.split(",")[0].strip() or None

    def _compute_distance(self, tag_name: str, node: str) -> int:
        """Count the commits between a tag and ``node``.

        Mirrors ``git describe --long``: every commit in the range is
        counted, the tagged commit itself is not.
        """
        return max(0, self._count_revset(f'"{tag_name}"::{node}') - 1)

    def _count_ancestors(self, node: str) -> int:
        """Count the ancestors of ``node``, excluding jj's virtual root."""
        return self._count_revset(f"::{node} ~ root()")

    def count_all_nodes(self) -> int:
        node = self.node()
        return self._count_ancestors(node) if node is not None else 0

    def get_scm_version(self) -> ScmVersion | None:
        config = self.config

        # first command in the process -- refreshes the working-copy commit
        # so that the emptiness of ``@`` below reflects uncommitted edits
        dirty = self.is_dirty()

        node = self.node()
        tag_name = self._find_latest_tag()

        if tag_name is not None:
            distance = 0 if node is None else self._compute_distance(tag_name, node)
            version = meta(
                tag=tag_name,
                distance=distance,
                dirty=dirty,
                node=None if node is None else "j" + node[:12],
                config=config,
            )
        else:
            tag = config.version_cls(config.fallback_version or "0.0")
            if node is None:
                distance = 0
                dirty = True
            else:
                distance = self._count_ancestors(node)
                node = "j" + node[:12]
            version = meta(
                tag=tag, distance=distance, dirty=dirty, node=node, config=config
            )

        branch = self.get_branch()
        node_date = self.get_head_date()

        if node_date is None:
            node_date = datetime.now(timezone.utc).date()

        return dataclasses.replace(version, branch=branch, node_date=node_date)

    def list_tracked_files(self, path: Path | str = "") -> list[str]:
        from .._file_finders import scm_find_files
        from .._file_finders._jj import _jj_ls_files_and_dirs

        base = str(path) if path else str(self.project_root)
        jj_files, jj_dirs = _jj_ls_files_and_dirs(
            str(self.path), timeout=self._subprocess_timeout
        )
        return scm_find_files(base, jj_files, jj_dirs)

    def is_file_tracked(self, path: Path) -> bool:
        res = self.run_jj(["file", "list", str(path)], needs_snapshot=True)
        output = res.parse_success(parse=str)
        return bool(output)


def get_working_directory(config: Configuration, root: _t.PathT) -> JjWorkdir | None:
    """Return the working directory (``JjWorkdir``)."""
    from .. import _discover as discover

    for potential_root in discover.walk_potential_roots(
        root, search_parents=config.search_parent_directories
    ):
        potential_wd = JjWorkdir.from_potential_worktree(potential_root, config)
        if potential_wd is not None:
            return potential_wd

    return JjWorkdir.from_potential_worktree(Path(root), config)


def parse(
    root: _t.PathT,
    config: Configuration,
) -> ScmVersion | None:
    """Parse version from a Jujutsu repository."""
    _require_command("jj")
    wd = get_working_directory(config, root)
    if wd:
        return wd.get_scm_version()
    return None
