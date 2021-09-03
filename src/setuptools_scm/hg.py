import os
from pathlib import Path

from .config import Configuration
from .scm_workdir import Workdir
from .utils import data_from_mime
from .utils import do_ex
from .utils import require_command
from .utils import trace
from .version import meta
from .version import tag_to_version


class HgWorkdir(Workdir):

    COMMAND = "hg"

    @classmethod
    def from_potential_worktree(cls, wd):
        require_command(cls.COMMAND)
        root, err, ret = do_ex("hg root", wd)
        if ret:
            return
        return cls(root)

    def get_meta(self, config):

        node, tags, bookmark, node_date = self.hg_log(
            ".", "{node}\n{tag}\n{bookmark}\n{date|shortdate}"
        ).split("\n")

        # TODO: support bookmarks and topics (but nowadays bookmarks are
        # mainly used to emulate Git branches, which is already supported with
        # the dedicated class GitWorkdirHgClient)

        branch, dirty, dirty_date = self.do(
            ["hg", "id", "-T", "{branch}\n{if(dirty, 1, 0)}\n{date|shortdate}"]
        ).split("\n")
        dirty = bool(int(dirty))

        if dirty:
            date = dirty_date
        else:
            date = node_date

        if all(c == "0" for c in node):
            trace("initial node", self.path)
            return meta("0.0", config=config, dirty=dirty, branch=branch)

        node = "h" + node[:7]

        tags = tags.split()
        if "tip" in tags:
            # tip is not a real tag
            tags = tags.remove("tip")

        if tags:
            tag = tags[0]
            tag = tag_to_version(tag)
            if tag:
                return meta(tag, dirty=dirty, branch=branch, config=config)

        try:
            tag = self.get_latest_normalizable_tag()
            dist = self.get_distance_revs(tag)
            if tag == "null":
                tag = "0.0"
                dist = int(dist) + 1

            if self.check_changes_since_tag(tag) or dirty:
                return meta(
                    tag,
                    distance=dist,
                    node=node,
                    dirty=dirty,
                    branch=branch,
                    config=config,
                    node_date=date,
                )
            else:
                return meta(tag, config=config)

        except ValueError:
            pass  # unpacking failed, old hg

    def hg_log(self, revset, template):
        cmd = ["hg", "log", "-r", revset, "-T", template]
        return self.do(cmd)

    def get_latest_normalizable_tag(self):
        # Gets all tags containing a '.' (see #229) from oldest to newest
        outlines = self.hg_log(
            revset="ancestors(.) and tag('re:\\.')",
            template="{tags}{if(tags, '\n', '')}",
        ).split()
        if not outlines:
            return "null"
        tag = outlines[-1].split()[-1]
        return tag

    def get_distance_revs(self, rev1, rev2="."):
        revset = f"({rev1}::{rev2})"
        out = self.hg_log(revset, ".")
        return len(out) - 1

    def check_changes_since_tag(self, tag):

        if tag == "0.0":
            return True

        revset = (
            "(branch(.)"  # look for revisions in this branch only
            f" and tag({tag!r})::."  # after the last tag
            # ignore commits that only modify .hgtags and nothing else:
            " and (merge() or file('re:^(?!\\.hgtags).*$'))"
            f" and not tag({tag!r}))"  # ignore the tagged commit itself
        )

        return bool(self.hg_log(revset, "."))


def parse(root, config=None):
    if not config:
        config = Configuration(root=root)

    if os.path.exists(os.path.join(root, ".hg/git")):
        paths, _, ret = do_ex("hg path", root)
        if not ret:
            for line in paths.split("\n"):
                if line.startswith("default ="):
                    path = Path(line.split()[2])
                    if path.name.endswith(".git") or (path / ".git").exists():
                        from .git import _git_parse_inner
                        from .hg_git import GitWorkdirHgClient

                        wd = GitWorkdirHgClient.from_potential_worktree(root)
                        if wd:
                            return _git_parse_inner(config, wd)

    wd = HgWorkdir.from_potential_worktree(config.absolute_root)

    if wd is None:
        return

    return wd.get_meta(config)


def archival_to_version(data, config: "Configuration | None" = None):
    trace("data", data)
    node = data.get("node", "")[:12]
    if node:
        node = "h" + node
    if "tag" in data:
        return meta(data["tag"], config=config)
    elif "latesttag" in data:
        return meta(
            data["latesttag"],
            distance=data["latesttagdistance"],
            node=node,
            config=config,
        )
    else:
        return meta("0.0", node=node, config=config)


def parse_archival(root, config=None):
    archival = os.path.join(root, ".hg_archival.txt")
    data = data_from_mime(archival)
    return archival_to_version(data, config=config)
