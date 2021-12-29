import os
from datetime import datetime

from .git import GitWorkdir
from .hg import HgWorkdir
from .utils import do_ex
from .utils import require_command
from .utils import trace


class GitWorkdirHgClient(GitWorkdir, HgWorkdir):
    COMMAND = "hg"

    @classmethod
    def from_potential_worktree(cls, wd):
        require_command(cls.COMMAND)
        root, err, ret = do_ex("hg root", wd)
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

    def _hg2git(self, hg_node):
        git_node = None
        with open(os.path.join(self.path, ".hg/git-mapfile")) as file:
            for line in file:
                if hg_node in line:
                    git_node, hg_node = line.split()
                    break
        return git_node

    def node(self):
        hg_node = self.get_hg_node()
        if hg_node is None:
            return

        git_node = self._hg2git(hg_node)

        if git_node is None:
            # trying again after hg -> git
            self.do_ex("hg gexport")
            git_node = self._hg2git(hg_node)

            if git_node is None:
                trace("Cannot get git node so we use hg node", hg_node)

                if hg_node == "0" * len(hg_node):
                    # mimic Git behavior
                    return None

                return hg_node

        return git_node[:7]

    def count_all_nodes(self):
        revs, _, _ = self.do_ex("hg log -r 'ancestors(.)' -T '.'")
        return len(revs)

    def default_describe(self):
        """
        Tentative to reproduce the output of

        `git describe --dirty --tags --long --match *[0-9]*`

        """
        hg_tags, _, ret = self.do_ex(
            [
                "hg",
                "log",
                "-r",
                "(reverse(ancestors(.)) and tag(r're:[0-9]'))",
                "-T",
                "{tags}{if(tags, ' ', '')}",
            ]
        )
        if ret:
            return None, None, None
        hg_tags = hg_tags.split()

        if not hg_tags:
            return None, None, None

        git_tags = {}
        with open(os.path.join(self.path, ".hg/git-tags")) as file:
            for line in file:
                node, tag = line.split()
                git_tags[tag] = node

        # find the first hg tag which is also a git tag
        for tag in hg_tags:
            if tag in git_tags:
                break

        out, _, ret = self.do_ex(["hg", "log", "-r", f"'{tag}'::.", "-T", "."])
        if ret:
            return None, None, None
        distance = len(out) - 1

        node = self.node()
        desc = f"{tag}-{distance}-g{node}"

        if self.is_dirty():
            desc += "-dirty"

        return desc, None, 0
