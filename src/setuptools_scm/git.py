from .config import Configuration
from .utils import do_ex, trace, require_command
from .version import meta
from datetime import datetime, date
import os
from os.path import isfile, join
import warnings


from os.path import samefile


DEFAULT_DESCRIBE = "git describe --dirty --tags --long --match *[0-9]*"


class GitWorkdir:
    """experimental, may change at any time"""

    COMMAND = "git"

    def __init__(self, path):
        self.path = path

    def do_ex(self, cmd):
        return do_ex(cmd, cwd=self.path)

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
            # TODO: understand the diff between these 2 commands
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


class GitWorkdirHgClient(GitWorkdir):
    COMMAND = "hg"

    @classmethod
    def from_potential_worktree(cls, wd):
        require_command(cls.COMMAND)
        root, _, ret = do_ex("hg root", wd)
        if ret:
            return
        return cls(root)

    def is_dirty(self):
        out, _, _ = self.do_ex("hg id -T '{dirty}'")
        return bool(out)

    def get_branch(self):
        branch, err, ret = self.do_ex("hg id -T {bookmarks}")
        if ret:
            trace("branch err", branch, err, ret)
            return
        return branch

    def get_head_date(self):
        date_part, err, ret = self.do_ex("hg log -r . -T {shortdate(date)}")
        if ret:
            trace("head date err", date_part, err, ret)
            return
        return datetime.strptime(date_part, r"%Y-%m-%d").date()

    def is_shallow(self):
        return False

    def fetch_shallow(self):
        pass

    def get_hg_node(self):
        node, _, ret = self.do_ex("hg log -r . -T {node}")
        if not ret:
            return node

    def node(self):
        hg_node = self.get_hg_node()
        if hg_node is None:
            return

        with open(os.path.join(self.path, ".hg/git-mapfile"), "r") as file:
            for line in file:
                if hg_node in line:
                    git_node, hg_node = line.split()
                    break

        return git_node[:7]

    def count_all_nodes(self):
        revs, _, _ = self.do_ex("hg log -r 'ancestors(.)' -T '.'")
        return len(revs) + 1

    def default_describe(self):
        """
        Tentative to reproduce the output of

        `git describe --dirty --tags --long --match *[0-9]*`

        """
        hg_tags, _, ret = self.do_ex(
            "hg log -r reverse(ancestors(.)) -T {tags}{if(tags, ' ', '')}"
        )
        if ret:
            return None, None, None
        hg_tags = hg_tags.split()

        git_tags = {}
        with open(os.path.join(self.path, ".hg/git-tags"), "r") as file:
            for line in file:
                node, tag = line.split()
                git_tags[tag] = node

        # find the first hg tag which is also a git tag
        # TODO: also check for match *[0-9]*
        for tag in hg_tags:
            if tag in git_tags:
                break

        out, _, ret = self.do_ex("hg log -r .::" + tag + " -T .")
        if ret:
            return None, None, None
        distance = len(out) - 1

        node = self.node()
        desc = f"{tag}-{distance}-g{node}"

        if self.is_dirty():
            desc += "-dirty"

        return desc, None, 0


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


def parse(root, describe_command=None, pre_parse=warn_on_shallow, config=None):
    """
    :param pre_parse: experimental pre_parse action, may change at any time
    """
    if not config:
        config = Configuration(root=root)

    wd = GitWorkdir.from_potential_worktree(config.absolute_root)
    if wd is None:
        wd = GitWorkdirHgClient.from_potential_worktree(config.absolute_root)
    if wd is None:
        return
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
    else:
        # If 'git git_describe_command' failed, try to get the information otherwise.
        tag = "0.0"
        node = wd.node()
        if node is None:
            distance = 0
        else:
            distance = wd.count_all_nodes()
            node = "g" + node
        if distance == 0:
            distance = None
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
