from __future__ import annotations

import dataclasses
import logging
import os
import re
import shlex
import warnings
from datetime import date
from datetime import datetime
from os.path import samefile
from pathlib import Path
from subprocess import CompletedProcess
from typing import Callable
from typing import Sequence
from typing import TYPE_CHECKING

from . import _types as _t
from . import Configuration
from ._run_cmd import require_command
from ._run_cmd import run
from .integration import data_from_mime
from .scm_workdir import Workdir
from .version import meta
from .version import ScmVersion
from .version import tag_to_version

if TYPE_CHECKING:
    from . import hg_git
log = logging.getLogger(__name__)

REF_TAG_RE = re.compile(r"(?<=\btag: )([^,]+)\b")
DESCRIBE_UNSUPPORTED = "%(describe"

# If testing command in shell make sure to quote the match argument like
# '*[0-9]*' as it will expand before being sent to git if there are any matching
# files in current directory.
DEFAULT_DESCRIBE = [
    "git",
    "describe",
    "--dirty",
    "--tags",
    "--long",
    "--match",
    "*[0-9]*",
]


def run_git(
    args: Sequence[str | os.PathLike[str]], rootdir: Path, *, check: bool = False
) -> CompletedProcess[str]:
    return run(["git", "--git-dir", rootdir / ".git", *args], cwd=rootdir, check=check)


class GitWorkdir(Workdir):
    """experimental, may change at any time"""

    COMMAND = "git"

    @classmethod
    def from_potential_worktree(cls, wd: _t.PathT) -> GitWorkdir | None:
        require_command(cls.COMMAND)
        wd = os.path.abspath(wd)
        res = run_git(["rev-parse", "--show-prefix"], Path(wd))

        real_wd = res.stdout[:-1]  # remove the trailing pathsep
        if res.returncode:
            return None
        if not real_wd:
            real_wd = wd
        else:
            assert wd.replace("\\", "/").endswith(real_wd)
            # In windows wd contains ``\`` which should be replaced by ``/``
            # for this assertion to work.  Length of string isn't changed by replace
            # ``\\`` is just and escape for `\`
            real_wd = wd[: -len(real_wd)]
        log.debug("real root %s", real_wd)
        if not samefile(real_wd, wd):
            return None

        return cls(real_wd)

    def is_dirty(self) -> bool:
        res = run_git(["status", "--porcelain", "--untracked-files=no"], self.path)
        return bool(res.stdout)

    def get_branch(self) -> str | None:
        res = run_git(["rev-parse", "--abbrev-ref", "HEAD"], self.path)
        if res.returncode:
            log.info("branch err (abbrev-err) %s", res)
            res = run_git(["symbolic-ref", "--short", "HEAD"], self.path)
        if res.returncode:
            log.warning("branch err (symbolic-ref): %s", res)
            return None
        return res.stdout

    def get_head_date(self) -> date | None:
        res = run_git(
            ["-c", "log.showSignature=false", "log", "-n", "1", "HEAD", "--format=%cI"],
            self.path,
        )
        if res.returncode:
            log.warning("timestamp err %s", res)
            return None
        if "%c" in res.stdout:
            log.warning("git too old -> timestamp is %s", res.stdout)
            return None
        return datetime.fromisoformat(res.stdout).date()

    def is_shallow(self) -> bool:
        return self.path.joinpath(".git/shallow").is_file()

    def fetch_shallow(self) -> None:
        run_git(["fetch", "--unshallow"], self.path, check=True)

    def node(self) -> str | None:
        res = run_git(["rev-parse", "--verify", "--quiet", "HEAD"], self.path)
        if not res.returncode:
            return res.stdout[:7]
        else:
            return None

    def count_all_nodes(self) -> int:
        res = run_git(["rev-list", "HEAD"], self.path)
        return res.stdout.count("\n") + 1

    def default_describe(self) -> CompletedProcess[str]:
        return run_git(DEFAULT_DESCRIBE[1:], self.path)


def warn_on_shallow(wd: GitWorkdir) -> None:
    """experimental, may change at any time"""
    if wd.is_shallow():
        warnings.warn(f'"{wd.path}" is shallow and may cause errors')


def fetch_on_shallow(wd: GitWorkdir) -> None:
    """experimental, may change at any time"""
    if wd.is_shallow():
        warnings.warn(f'"{wd.path}" was shallow, git fetch was used to rectify')
        wd.fetch_shallow()


def fail_on_shallow(wd: GitWorkdir) -> None:
    """experimental, may change at any time"""
    if wd.is_shallow():
        raise ValueError(
            f'{wd.path} is shallow, please correct with "git fetch --unshallow"'
        )


def get_working_directory(config: Configuration, root: _t.PathT) -> GitWorkdir | None:
    """
    Return the working directory (``GitWorkdir``).
    """

    if config.parent:  # todo broken
        return GitWorkdir.from_potential_worktree(config.parent)

    if config.search_parent_directories:
        return search_parent(root)

    return GitWorkdir.from_potential_worktree(root)


def parse(
    root: _t.PathT,
    config: Configuration,
    describe_command: str | list[str] | None = None,
    pre_parse: Callable[[GitWorkdir], None] = warn_on_shallow,
) -> ScmVersion | None:
    """
    :param pre_parse: experimental pre_parse action, may change at any time
    """
    wd = get_working_directory(config, root)
    if wd:
        return _git_parse_inner(
            config, wd, describe_command=describe_command, pre_parse=pre_parse
        )
    else:
        return None


def version_from_describe(
    wd: GitWorkdir | hg_git.GitWorkdirHgClient,
    config: Configuration,
    describe_command: _t.CMD_TYPE | None,
) -> ScmVersion | None:
    pass

    if config.git_describe_command is not None:
        describe_command = config.git_describe_command

    if describe_command is not None:
        if isinstance(describe_command, str):
            describe_command = shlex.split(describe_command)
            # todo: figure how ot ensure git with gitdir gets correctly invoked
            assert describe_command[0] == "git", describe_command
        describe_res = run_git(describe_command[1:], wd.path)
    else:
        describe_res = wd.default_describe()

    distance: int | None
    node: str | None
    if describe_res.returncode == 0:
        tag, distance, node, dirty = _git_parse_describe(describe_res.stdout)
        if distance == 0 and not dirty:
            distance = None
        return meta(tag=tag, distance=distance, dirty=dirty, node=node, config=config)
    return None


def _git_parse_inner(
    config: Configuration,
    wd: GitWorkdir | hg_git.GitWorkdirHgClient,
    pre_parse: None | (Callable[[GitWorkdir | hg_git.GitWorkdirHgClient], None]) = None,
    describe_command: _t.CMD_TYPE | None = None,
) -> ScmVersion:
    if pre_parse:
        pre_parse(wd)

    version = version_from_describe(wd, config, describe_command)

    if version is None:
        # If 'git git_describe_command' failed, try to get the information otherwise.
        tag = config.version_cls("0.0")
        node = wd.node()
        if node is None:
            distance = 0
        else:
            distance = wd.count_all_nodes()
            node = "g" + node
        dirty = wd.is_dirty()
        version = meta(
            tag=tag, distance=distance, dirty=dirty, node=node, config=config
        )

    branch = wd.get_branch()
    node_date = wd.get_head_date() or date.today()
    return dataclasses.replace(version, branch=branch, node_date=node_date)


def _git_parse_describe(
    describe_output: str,
) -> tuple[str, int | None, str | None, bool]:
    # 'describe_output' looks e.g. like 'v1.5.0-0-g4060507' or
    # 'v1.15.1rc1-37-g9bd1298-dirty'.
    # It may also just be a bare tag name if this is a tagged commit and we are
    # parsing a .git_archival.txt file.

    if describe_output.endswith("-dirty"):
        dirty = True
        describe_output = describe_output[:-6]
    else:
        dirty = False

    split = describe_output.rsplit("-", 2)
    if len(split) < 3:  # probably a tagged commit
        tag = describe_output
        number = None
        node = None
    else:
        tag, number_, node = split
        number = int(number_)
    return tag, number, node, dirty


def search_parent(dirname: _t.PathT) -> GitWorkdir | None:
    """
    Walk up the path to find the `.git` directory.
    :param dirname: Directory from which to start searching.
    """

    # Code based on:
    # https://github.com/gitpython-developers/GitPython/blob/main/git/repo/base.py

    curpath = os.path.abspath(dirname)

    while curpath:
        try:
            wd = GitWorkdir.from_potential_worktree(curpath)
        except Exception:
            wd = None

        if wd is not None:
            return wd

        curpath, tail = os.path.split(curpath)

        if not tail:
            return None
    return None


def archival_to_version(
    data: dict[str, str], config: Configuration
) -> ScmVersion | None:
    node: str | None
    log.debug("data %s", data)
    archival_describe = data.get("describe-name", DESCRIBE_UNSUPPORTED)
    if DESCRIBE_UNSUPPORTED in archival_describe:
        warnings.warn("git archive did not support describe output")
    else:
        tag, number, node, _ = _git_parse_describe(archival_describe)
        return meta(
            tag,
            config=config,
            distance=None if number == 0 else number,
            node=node,
        )

    for ref in REF_TAG_RE.findall(data.get("ref-names", "")):
        version = tag_to_version(ref, config)
        if version is not None:
            return meta(version, config=config)
    else:
        node = data.get("node")
        if node is None:
            return None
        elif "$FORMAT" in node.upper():
            warnings.warn("unexported git archival found")
            return None
        else:
            return meta("0.0", node=node, config=config)


def parse_archival(root: _t.PathT, config: Configuration) -> ScmVersion | None:
    archival = os.path.join(root, ".git_archival.txt")
    data = data_from_mime(archival)
    return archival_to_version(data, config=config)
