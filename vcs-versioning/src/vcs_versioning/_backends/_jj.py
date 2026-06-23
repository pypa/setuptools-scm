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


def run_jj(
    args: Sequence[str | os.PathLike[str]],
    repo: Path,
    *,
    check: bool = False,
    timeout: int | None = None,
) -> _CompletedProcess:
    return _run(
        ["jj", "--no-pager", "--repository", str(repo), *args],
        cwd=repo,
        check=check,
        timeout=timeout,
    )


class JjWorkdir(Workdir):
    """Work directory backed by Jujutsu (jj)."""

    def run_jj(
        self,
        args: Sequence[str | os.PathLike[str]],
        *,
        check: bool = False,
        timeout: int | None = None,
    ) -> _CompletedProcess:
        return run_jj(
            args, self.path, check=check, timeout=timeout or self._subprocess_timeout
        )

    @classmethod
    def from_potential_worktree(
        cls, wd: Path, config: Configuration | None = None
    ) -> JjWorkdir | None:
        wd = Path(wd).resolve()
        if not (wd / ".jj").is_dir():
            return None

        timeout = config.env.subprocess_timeout if config is not None else None
        res = run_jj(["root"], wd, timeout=timeout)
        root = res.parse_success(parse=str)
        if root is None:
            return None

        result = cls(Path(root))
        result._config = config
        return result

    def is_dirty(self) -> bool:
        res = self.run_jj(["diff", "--summary"])
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

    def node(self) -> str | None:
        res = self.run_jj(
            [
                "log",
                "--no-graph",
                "-r",
                "latest(::@ ~ (empty() ~ tags()))",
                "-T",
                "commit_id",
            ],
        )
        result = res.parse_success(parse=str)
        return result if result else None

    def _find_latest_tag(self) -> tuple[str | None, str | None]:
        """Find the latest tagged ancestor of the working copy.

        Returns (tag_name, commit_id) or (None, None) if no tags found.
        """
        res = self.run_jj(
            [
                "log",
                "--no-graph",
                "-r",
                "latest(heads(::@ & tags()))",
                "-T",
                'tags.map(|t| t.name()).join(",") ++ "\\n" ++ commit_id',
            ],
        )
        output = res.parse_success(parse=str)
        if not output:
            return None, None

        lines = output.strip().split("\n")
        if len(lines) < 2:
            return None, None

        tag_names = lines[0].strip()
        commit_id = lines[1].strip()
        if not tag_names:
            return None, None

        # Take the first tag if multiple point at the same commit
        tag = tag_names.split(",")[0].strip()
        return tag, commit_id

    def _compute_distance(self, tag_name: str) -> int:
        """Count non-empty commits between a tag and the working copy.

        In jj's model the working copy ``@`` is a real commit.  If it
        contains changes it is counted as one commit of distance, which
        is the semantically correct representation.
        """
        res = self.run_jj(
            [
                "log",
                "--no-graph",
                "-r",
                f'"{tag_name}"::@ ~ empty()',
                "-T",
                'commit_id ++ "\\n"',
            ],
        )
        output = res.parse_success(parse=str)
        if not output:
            return 0

        # Each non-empty line is a commit; subtract 1 for the tagged commit itself
        commits = [line for line in output.strip().split("\n") if line.strip()]
        return max(0, len(commits) - 1)

    def count_all_nodes(self) -> int:
        res = self.run_jj(
            [
                "log",
                "--no-graph",
                "-r",
                "::@ ~ empty()",
                "-T",
                'commit_id ++ "\\n"',
            ],
        )
        output = res.parse_success(parse=str)
        if not output:
            return 0
        return len([line for line in output.strip().split("\n") if line.strip()])

    def get_scm_version(self) -> ScmVersion | None:
        config = self.config

        tag_name, _tag_commit = self._find_latest_tag()
        dirty = self.is_dirty()

        if tag_name is not None:
            distance = self._compute_distance(tag_name)
            node = self.node()
            if node:
                node = "j" + node[:12]
            version = meta(
                tag=tag_name,
                distance=distance,
                dirty=dirty,
                node=node,
                config=config,
            )
        else:
            tag = config.version_cls(config.fallback_version or "0.0")
            node = self.node()
            if node is None:
                distance = 0
                dirty = True
            else:
                distance = self.count_all_nodes()
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
        res = self.run_jj(["file", "list", str(path)])
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
