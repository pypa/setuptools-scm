import os
import warnings
from datetime import date
from datetime import datetime
from os.path import isfile
from os.path import join
from os.path import samefile

from .config import Configuration
from .scm_workdir import Workdir
from .utils import do_ex
from .utils import require_command
from .utils import trace
from .version import meta

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


class GitWorkdir(Workdir):
    """experimental, may change at any time"""

    COMMAND = "git"

    @classmethod
    def from_potential_worktree(cls, wd):
        require_command(cls.COMMAND)
        wd = os.path.abspath(wd)
        real_wd, _, ret = do_ex("git rev-parse --show-prefix", wd)
        real_wd = real_wd[:-1]  # remove the trailing pathsep
        if ret:
            return
        if not real_wd:
            real_wd = wd
        else:
            assert wd.replace("\\", "/").endswith(real_wd)
            # In windows wd contains ``\`` which should be replaced by ``/``
            # for this assertion to work.  Length of string isn't changed by replace
            # ``\\`` is just and escape for `\`
            real_wd = wd[: -len(real_wd)]
        trace("real root", real_wd)
        if not samefile(real_wd, wd):
            return

        return cls(real_wd)

    def is_dirty(self):
        out, _, _ = self.do_ex("git status --porcelain --untracked-files=no")
        return bool(out)

    def get_branch(self):
        branch, err, ret = self.do_ex("git rev-parse --abbrev-ref HEAD")
        if ret:
            trace("branch err", branch, err, ret)
            branch, err, ret = self.do_ex("git symbolic-ref --short HEAD")
            if ret:
                trace("branch err (symbolic-ref)", branch, err, ret)
                branch = None
        return branch

    def get_head_date(self):
        timestamp, err, ret = self.do_ex("git log -n 1 HEAD --format=%cI")
        if ret:
            trace("timestamp err", timestamp, err, ret)
            return
        # TODO, when dropping python3.6 use fromiso
        date_part = timestamp.split("T")[0]
        if "%c" in date_part:
            trace("git too old -> timestamp is ", timestamp)
            return None
        return datetime.strptime(date_part, r"%Y-%m-%d").date()

    def is_shallow(self):
        return isfile(join(self.path, ".git/shallow"))

    def fetch_shallow(self):
        self.do_ex("git fetch --unshallow")

    def node(self):
        node, _, ret = self.do_ex("git rev-parse --verify --quiet HEAD")
        if not ret:
            return node[:7]

    def count_all_nodes(self):
        revs, _, _ = self.do_ex("git rev-list HEAD")
        return revs.count("\n") + 1

    def default_describe(self):
        return self.do_ex(DEFAULT_DESCRIBE)


def warn_on_shallow(wd):
    """experimental, may change at any time"""
    if wd.is_shallow():
        warnings.warn(f'"{wd.path}" is shallow and may cause errors')


def fetch_on_shallow(wd):
    """experimental, may change at any time"""
    if wd.is_shallow():
        warnings.warn(f'"{wd.path}" was shallow, git fetch was used to rectify')
        wd.fetch_shallow()


def fail_on_shallow(wd):
    """experimental, may change at any time"""
    if wd.is_shallow():
        raise ValueError(
            f'{wd.path} is shallow, please correct with "git fetch --unshallow"'
        )


def get_working_directory(config):
    """
    Return the working directory (``GitWorkdir``).
    """

    if config.parent:
        return GitWorkdir.from_potential_worktree(config.parent)

    if config.search_parent_directories:
        return search_parent(config.absolute_root)

    return GitWorkdir.from_potential_worktree(config.absolute_root)


def parse(root, describe_command=None, pre_parse=warn_on_shallow, config=None):
    """
    :param pre_parse: experimental pre_parse action, may change at any time
    """
    if not config:
        config = Configuration(root=root)

    wd = get_working_directory(config)
    if wd:
        return _git_parse_inner(
            config, wd, describe_command=describe_command, pre_parse=pre_parse
        )


def _git_parse_inner(config, wd, pre_parse=None, describe_command=None):
    if pre_parse:
        pre_parse(wd)

    if config.git_describe_command is not None:
        describe_command = config.git_describe_command

    if describe_command is not None:
        out, _, ret = wd.do_ex(describe_command)
    else:
        out, _, ret = wd.default_describe()

    if ret == 0:
        tag, distance, node, dirty = _git_parse_describe(out)
        if distance == 0 and not dirty:
            distance = None
    else:
        # If 'git git_describe_command' failed, try to get the information otherwise.
        tag = "0.0"
        node = wd.node()
        if node is None:
            distance = 0
        else:
            distance = wd.count_all_nodes()
            node = "g" + node
        dirty = wd.is_dirty()

    branch = wd.get_branch()
    node_date = wd.get_head_date() or date.today()

    return meta(
        tag,
        branch=branch,
        node=node,
        node_date=node_date,
        distance=distance,
        dirty=dirty,
        config=config,
    )


def _git_parse_describe(describe_output):
    # 'describe_output' looks e.g. like 'v1.5.0-0-g4060507' or
    # 'v1.15.1rc1-37-g9bd1298-dirty'.

    if describe_output.endswith("-dirty"):
        dirty = True
        describe_output = describe_output[:-6]
    else:
        dirty = False

    tag, number, node = describe_output.rsplit("-", 2)
    number = int(number)
    return tag, number, node, dirty


def search_parent(dirname):
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
