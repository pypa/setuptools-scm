import os
from .config import Configuration
from .utils import do_ex, do, trace, data_from_mime, require_command
from .version import meta, tags_to_versions, tag_to_version


class Workdir:
    def __init__(self, path):
        require_command(self.COMMAND)
        self.path = path

    def do_ext(self, cmd):
        return do_ex(cmd, cwd=self.path)

    def do(self, cmd):
        return do(cmd, cwd=self.path)


class HgWorkdir(Workdir):

    COMMAND = "hg"

    @classmethod
    def from_potential_worktree(cls, wd):
        require_command(cls.COMMAND)
        root, err, ret = do_ex("hg root", wd)
        if ret:
            print(err)
            return
        return cls(root)

    def get_meta(self, config):

        node, tags, bookmark, node_date = self.hg_log(
            ".", "{node}\n{tag}\n{bookmark}\n{date|shortdate}"
        ).split("\n")

        branch, dirty, dirty_date = self.do(
            ["hg", "id", "-T", "{branch}\n{if(dirty, 1, 0)}\n{date|shortdate}"]
        ).split("\n")
        dirty = bool(int(dirty))

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
    if os.path.exists(os.path.join(root, ".hg/git")):
        from .git import parse as git_parse

        return git_parse(root, config=config)

    if not config:
        config = Configuration(root=root)

    wd = HgWorkdir.from_potential_worktree(config.absolute_root)

    if wd is None:
        return

    return wd.get_meta(config)


def archival_to_version(data, config=None):
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
