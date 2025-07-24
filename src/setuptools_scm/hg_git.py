from __future__ import annotations

import logging
import os

from contextlib import suppress
from datetime import date
from pathlib import Path

from . import _types as _t
from ._run_cmd import CompletedProcess as _CompletedProcess
from ._run_cmd import run as _run
from .git import GitWorkdir
from .hg import HG_COMMAND
from .hg import HgWorkdir

log = logging.getLogger(__name__)

_FAKE_GIT_DESCRIBE_ERROR = _CompletedProcess(
    "fake git describe output for hg",
    1,
    "<>hg git failed to describe",
)


class GitWorkdirHgClient(GitWorkdir, HgWorkdir):
    @classmethod
    def from_potential_worktree(cls, wd: _t.PathT) -> GitWorkdirHgClient | None:
        res = _run([HG_COMMAND, "root"], cwd=wd).parse_success(parse=Path)
        if res is None:
            return None
        return cls(res)

    def is_dirty(self) -> bool:
        res = _run([HG_COMMAND, "id", "-T", "{dirty}"], cwd=self.path, check=True)
        return bool(res.stdout)

    def get_branch(self) -> str | None:
        res = _run([HG_COMMAND, "id", "-T", "{bookmarks}"], cwd=self.path)
        if res.returncode:
            log.info("branch err %s", res)
            return None
        return res.stdout

    def get_head_date(self) -> date | None:
        return _run(
            [HG_COMMAND, "log", "-r", ".", "-T", "{shortdate(date)}"], cwd=self.path
        ).parse_success(parse=date.fromisoformat, error_msg="head date err")

    def get_dirty_tag_date(self) -> date | None:
        """Get the latest modification time of changed files in the working directory.

        Returns the date of the most recently modified file that has changes,
        or None if no files are changed or if an error occurs.
        """
        if not self.is_dirty():
            return None

        try:
            from datetime import datetime
            from datetime import timezone

            # Get list of changed files using hg status
            status_res = _run([HG_COMMAND, "status", "-m", "-a", "-r"], cwd=self.path)
            if status_res.returncode != 0:
                return None

            changed_files = []
            for line in status_res.stdout.strip().split("\n"):
                if line and len(line) > 2:
                    # Format is "M filename" or "A filename" etc.
                    filepath = line[2:]  # Skip status char and space
                    changed_files.append(filepath)

            if not changed_files:
                return None

            latest_mtime = 0.0
            for filepath in changed_files:
                full_path = self.path / filepath
                try:
                    file_stat = full_path.stat()
                    latest_mtime = max(latest_mtime, file_stat.st_mtime)
                except OSError:
                    # File might not exist or be accessible, skip it
                    continue

            if latest_mtime > 0:
                # Convert to UTC date
                dt = datetime.fromtimestamp(latest_mtime, timezone.utc)
                return dt.date()

        except Exception as e:
            # Use the parent's log module
            import logging

            log = logging.getLogger(__name__)
            log.debug("Failed to get dirty tag date: %s", e)

        return None

    def is_shallow(self) -> bool:
        return False

    def fetch_shallow(self) -> None:
        pass

    def get_hg_node(self) -> str | None:
        res = _run([HG_COMMAND, "log", "-r", ".", "-T", "{node}"], cwd=self.path)
        if res.returncode:
            return None
        else:
            return res.stdout

    def _hg2git(self, hg_node: str) -> str | None:
        with suppress(FileNotFoundError):
            with open(os.path.join(self.path, ".hg/git-mapfile")) as map_items:
                for item in map_items:
                    if hg_node in item:
                        git_node, hg_node = item.split()
                        return git_node
        return None

    def node(self) -> str | None:
        hg_node = self.get_hg_node()
        if hg_node is None:
            return None

        git_node = self._hg2git(hg_node)

        if git_node is None:
            # trying again after hg -> git
            _run([HG_COMMAND, "gexport"], cwd=self.path)
            git_node = self._hg2git(hg_node)

            if git_node is None:
                log.debug("Cannot get git node so we use hg node %s", hg_node)

                if hg_node == "0" * len(hg_node):
                    # mimic Git behavior
                    return None

                return hg_node

        return git_node[:7]

    def count_all_nodes(self) -> int:
        res = _run([HG_COMMAND, "log", "-r", "ancestors(.)", "-T", "."], cwd=self.path)
        return len(res.stdout)

    def default_describe(self) -> _CompletedProcess:
        """
        Tentative to reproduce the output of

        `git describe --dirty --tags --long --match *[0-9]*`

        """
        res = _run(
            [
                HG_COMMAND,
                "log",
                "-r",
                "(reverse(ancestors(.)) and tag(r're:v?[0-9].*'))",
                "-T",
                "{tags}{if(tags, ' ', '')}",
            ],
            cwd=self.path,
        )
        if res.returncode:
            return _FAKE_GIT_DESCRIBE_ERROR
        hg_tags: list[str] = res.stdout.split()

        if not hg_tags:
            return _FAKE_GIT_DESCRIBE_ERROR

        with self.path.joinpath(".hg/git-tags").open() as fp:
            git_tags: dict[str, str] = dict(line.split()[::-1] for line in fp)

        tag: str
        for hg_tag in hg_tags:
            if hg_tag in git_tags:
                tag = hg_tag
                break
        else:
            logging.warning("tag not found hg=%s git=%s", hg_tags, git_tags)
            return _FAKE_GIT_DESCRIBE_ERROR

        res = _run([HG_COMMAND, "log", "-r", f"'{tag}'::.", "-T", "."], cwd=self.path)
        if res.returncode:
            return _FAKE_GIT_DESCRIBE_ERROR
        distance = len(res.stdout) - 1

        node = self.node()
        assert node is not None
        desc = f"{tag}-{distance}-g{node}"

        if self.is_dirty():
            desc += "-dirty"
        log.debug("faked describe %r", desc)
        return _CompletedProcess(
            ["setuptools-scm", "faked", "describe"],
            returncode=0,
            stdout=desc,
            stderr="",
        )
