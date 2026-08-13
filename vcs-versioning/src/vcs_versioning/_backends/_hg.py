from __future__ import annotations

import dataclasses
import datetime
import logging
import os
import re
from pathlib import Path
from typing import Any

from .. import _types as _t
from .._config import Configuration
from .._integration import data_from_mime
from .._run_cmd import CompletedProcess
from .._run_cmd import require_command as _require_command
from .._run_cmd import run as _run
from .._scm_version import ScmVersion, meta, tag_to_version
from .._version_cls import Version
from .._version_schemes import format_version
from ._scm_workdir import (
    STRICT_DIAGNOSTIC,
    Workdir,
    config_location,
    get_latest_file_mtime,
    report_once,
)

log = logging.getLogger(__name__)

_HG_PSEUDO_TAGS = frozenset({"tip", "qbase", "qtip", "qparent"})

_KEEP: Any = object()
"""Sentinel for "use the configured value" -- ``None`` is a real strictness."""


def hg_tag_pattern(config: Configuration, strict: bool | None = _KEEP) -> str:
    """Build the Mercurial regex ``latesttag()`` is given from tag config.

    *strict* overrides ``config.tag.strict``, which the diagnostics use to ask
    what the other setting would have selected.
    """
    if strict is _KEEP:
        strict = config.tag.strict
    prefix = re.escape(config.tag.prefix) if config.tag.prefix else ""
    if strict:
        # Require at least one dot in the version part
        return rf"{prefix}\d+\.\d+"
    else:
        return rf"{prefix}\d+"


def matches_tag_pattern(
    tag: str, config: Configuration, strict: bool | None = _KEEP
) -> bool:
    """Whether *tag* satisfies the configured strictness.

    The pattern is the same one ``latesttag()`` is given on the distance path,
    so both paths agree about which tags count as version tags.
    """
    return re.search(hg_tag_pattern(config, strict), tag) is not None


def select_tag(
    tags: list[str], config: Configuration, strict: bool | None = _KEEP
) -> str | None:
    """Pick the version tag to use from the tags on the current changeset.

    Pre-filters with tag_regex so non-version tags are silently skipped
    without emitting warnings from tag_to_version().
    Strips tag.prefix before matching when configured.

    Under ``tag.strict = true`` a tag that is not version-shaped is
    rejected outright rather than falling back to a looser match, so a
    changeset carrying only event-style tags falls through to the distance
    path -- the same thing ``git describe --match`` does (#1495).
    """
    if strict is _KEEP:
        strict = config.tag.strict
    tag_prefix = config.tag.prefix
    for tag_str in tags:
        check_str = tag_str
        if tag_prefix and tag_str.startswith(tag_prefix):
            check_str = tag_str[len(tag_prefix) :]
        if not config.tag.regex.match(check_str):
            log.debug("skipping non-version tag %r", tag_str)
            continue
        # only narrow when strictness was asked for, so the permissive
        # path keeps selecting exactly what it always has
        if strict and not matches_tag_pattern(tag_str, config, strict):
            log.debug("skipping tag %r: not version-shaped under tag.strict", tag_str)
            continue
        if tag_to_version(tag_str, config) is not None:
            return tag_str
    return None


def _rendered(version: ScmVersion | None, tag: str | None) -> str:
    """Render one side of the ``tag.strict`` comparison for the diagnostic."""
    if version is None:
        return "no matching tag, falling back to the fallback version"
    if tag is None:
        return format_version(version)
    return f"{format_version(version)} (from tag {tag!r})"


def _get_hg_command() -> str:
    """Read the hg command from resolved runtime settings.

    Only used by standalone callers (``has_command``, bare
    ``from_potential_worktree`` probes, file finders) that don't hold a
    ``Configuration``.  The chained API passes hg_command explicitly
    via ``config.env.hg_command``.
    """
    from .._environment import resolve_runtime_env

    return resolve_runtime_env().hg_command


def run_hg(
    args: list[str],
    cwd: _t.PathT,
    *,
    hg_command: str | None = None,
    timeout: int | None = None,
    **kwargs: Any,
) -> CompletedProcess:
    """Run mercurial command with the configured hg executable."""
    cmd = [hg_command or _get_hg_command(), *args]
    return _run(cmd, cwd=cwd, timeout=timeout, **kwargs)


class HgWorkdir(Workdir):
    def run_hg(
        self, args: list[str], *, check: bool = False, timeout: int | None = None
    ) -> CompletedProcess:
        return run_hg(
            args,
            self.path,
            check=check,
            timeout=timeout or self._subprocess_timeout,
            hg_command=self._hg_command,
        )

    @classmethod
    def from_potential_worktree(
        cls, wd: _t.PathT, config: Configuration | None = None
    ) -> HgWorkdir | None:
        hg_cmd = config.env.hg_command if config is not None else None
        timeout = config.env.subprocess_timeout if config is not None else None
        res = run_hg(["root"], wd, hg_command=hg_cmd, timeout=timeout)
        if res.returncode:
            return None
        return cls(Path(res.stdout), _config=config)

    def get_meta(self, config: Configuration) -> ScmVersion | None:
        # TODO: support bookmarks and topics (but nowadays bookmarks are
        # mainly used to emulate Git branches, which is already supported with
        # the dedicated class GitWorkdirHgClient)

        node_info = self._get_node_info()
        if node_info is None:
            return None

        node, tags_str, node_date_str = node_info
        branch_info = self._get_branch_info()
        branch, dirty, dirty_date = branch_info

        # Determine the appropriate node date
        node_date = self._get_node_date(dirty, node_date_str, dirty_date)

        # Handle initial/empty repository
        if self._is_initial_node(node):
            return self._create_initial_meta(config, dirty, branch, node_date)

        node = "h" + node
        tags = self._parse_tags(tags_str)

        # Try to get version from current tags
        result: ScmVersion | None
        tag_version = self._get_version_from_tags(tags, config)
        if tag_version:
            result = meta(tag_version, dirty=dirty, branch=branch, config=config)
        else:
            # Fall back to distance-based versioning
            result = self._get_distance_based_version(
                config, dirty, branch, node, node_date
            )

        if config.tag.strict is None:
            self._report_strict_divergence(config, tags, result)
        return result

    def _report_strict_divergence(
        self, config: Configuration, tags: list[str], result: ScmVersion | None
    ) -> None:
        """Report the coming ``tag.strict`` default when it changes the version.

        Mirrors the git backend: stay silent unless strict matching would
        select a different tag, so repositories the change cannot affect are
        never nagged (#1495).
        """
        permissive_tag = select_tag(tags, config, strict=False)
        strict_tag = select_tag(tags, config, strict=True)

        if permissive_tag is not None and permissive_tag == strict_tag:
            # the changeset is tagged with a version-shaped tag either way
            return
        if permissive_tag is None and strict_tag is None:
            # neither takes the exact-tag path, so compare the latest tags
            permissive_tag = self.get_latest_normalizable_tag(config, strict=False)
            if permissive_tag is None:
                return
            if matches_tag_pattern(permissive_tag, config, strict=True):
                # the permissive answer is itself version-shaped, and strict
                # matches a subset, so both paths land on the same tag
                return

        # whichever side found no tag on this changeset falls through to the
        # distance path, so name the tag it would count from there
        if permissive_tag is None:
            permissive_tag = self.get_latest_normalizable_tag(config, strict=False)
        if strict_tag is None:
            strict_tag = self.get_latest_normalizable_tag(config, strict=True)

        strict_config = dataclasses.replace(
            config, tag=dataclasses.replace(config.tag, strict=True)
        )
        strict_result = self.get_meta(strict_config)
        if (
            result is not None
            and strict_result is not None
            and format_version(result) == format_version(strict_result)
        ):
            # different tags, same resulting version -- nothing to act on
            return

        report_once(
            f"strict-divergence:{self.path}:{permissive_tag}:{strict_tag}",
            STRICT_DIAGNOSTIC,
            _rendered(result, permissive_tag),
            _rendered(strict_result, strict_tag),
            config_location(config),
        )

    def _get_node_info(self) -> tuple[str, str, str] | None:
        """Get node, tags, and date information from mercurial log."""
        try:
            node, tags_str, node_date_str = self.hg_log(
                ".", "{node}\n{tags}\n{date|shortdate}"
            ).split("\n")
            return node, tags_str, node_date_str
        except ValueError:
            log.exception("Failed to get node info")
            return None

    def _get_branch_info(self) -> tuple[str, bool, str]:
        """Get branch name, dirty status, and dirty date."""
        branch, dirty_str, dirty_date = self.run_hg(
            ["id", "-T", "{branch}\n{if(dirty, 1, 0)}\n{date|shortdate}"],
            check=True,
        ).stdout.split("\n")
        dirty = bool(int(dirty_str))
        return branch, dirty, dirty_date

    def _get_node_date(
        self, dirty: bool, node_date_str: str, dirty_date: str
    ) -> datetime.date:
        """Get the appropriate node date, preferring file modification times for dirty repos."""
        if dirty:
            file_mod_date = self.get_dirty_tag_date()
            if file_mod_date is not None:
                return file_mod_date
            # Fall back to hg id date for dirty repos
            return datetime.date.fromisoformat(dirty_date)
        else:
            return datetime.date.fromisoformat(node_date_str)

    def _is_initial_node(self, node: str) -> bool:
        """Check if this is an initial/empty repository node."""
        return node == "0" * len(node)

    def _create_initial_meta(
        self, config: Configuration, dirty: bool, branch: str, node_date: datetime.date
    ) -> ScmVersion:
        """Create metadata for initial/empty repository."""
        log.debug("initial node %s", self.path)
        return meta(
            Version("0.0"),
            config=config,
            dirty=dirty,
            branch=branch,
            node_date=node_date,
        )

    def _parse_tags(self, tags_str: str) -> list[str]:
        """Parse and filter tags from mercurial output.

        Filters out pseudo-tags that are never version tags:
        tip (hg internal), qbase/qtip/qparent (MQ extension).
        """
        return [t for t in tags_str.split() if t not in _HG_PSEUDO_TAGS]

    def _get_version_from_tags(
        self, tags: list[str], config: Configuration
    ) -> Version | None:
        """Try to get a version from the current tags."""
        tag_str = select_tag(tags, config)
        if tag_str is None:
            return None
        return tag_to_version(tag_str, config)

    def _get_distance_based_version(
        self,
        config: Configuration,
        dirty: bool,
        branch: str,
        node: str,
        node_date: datetime.date,
    ) -> ScmVersion | None:
        """Get version based on distance from latest tag."""
        try:
            tag_str = self.get_latest_normalizable_tag(config)
            if tag_str is None:
                dist = self.get_distance_revs("")
            else:
                dist = self.get_distance_revs(tag_str)

            if tag_str == "null" or tag_str is None:
                tag = Version("0.0")
                dist += 1
            else:
                maybe_tag = tag_to_version(tag_str, config=config)
                if maybe_tag is None:
                    # If tag conversion fails, treat as no tag found
                    tag = Version("0.0")
                    dist += 1
                else:
                    tag = maybe_tag

            if self.check_changes_since_tag(tag_str) or dirty:
                return meta(
                    tag,
                    distance=dist,
                    node=node,
                    dirty=dirty,
                    branch=branch,
                    config=config,
                    node_date=node_date,
                )
            else:
                return meta(tag, config=config, node_date=node_date)

        except ValueError:
            # unpacking failed, old hg
            log.exception("error")
            return None

    def hg_log(self, revset: str, template: str) -> str:
        return self.run_hg(
            ["log", "-r", revset, "-T", template],
            check=True,
        ).stdout

    def get_latest_normalizable_tag(
        self, config: Configuration | None = None, strict: bool | None = _KEEP
    ) -> str | None:
        if config is not None:
            pattern = hg_tag_pattern(config, strict)
        else:
            pattern = r"\."
        result = self.hg_log(
            revset=".",
            template=f"{{latesttag(r're:{pattern}')}}",
        )
        if not result or result == "null":
            return None
        # latesttag() returns colon-separated tags when multiple match
        # at the same distance; take the last one for consistency
        if ":" in result:
            result = result.rsplit(":", 1)[-1]
        return result

    def get_distance_revs(self, rev1: str, rev2: str = ".") -> int:
        revset = f"({rev1}::{rev2})"
        out = self.hg_log(revset, ".")
        return len(out) - 1

    def check_changes_since_tag(self, tag: str | None) -> bool:
        if tag == "0.0" or tag is None:
            return True

        revset = (
            "(branch(.)"  # look for revisions in this branch only
            f" and tag({tag!r})::."  # after the last tag
            # ignore commits that only modify .hgtags and nothing else:
            " and (merge() or file('re:^(?!\\.hgtags).*$'))"
            f" and not tag({tag!r}))"  # ignore the tagged commit itself
        )

        return bool(self.hg_log(revset, "."))

    def get_scm_version(self) -> ScmVersion | None:
        """Obtain version metadata from this hg work directory."""
        return self.get_meta(self.config)

    def list_tracked_files(self, path: Path | str = "") -> list[str]:
        """List files tracked by mercurial."""
        from .._file_finders import scm_find_files
        from .._file_finders._hg import _hg_ls_files_and_dirs

        base = str(path) if path else str(self.project_root)
        hg_files, hg_dirs = _hg_ls_files_and_dirs(
            str(self.path),
            hg_command=self._hg_command,
            timeout=self._subprocess_timeout,
        )
        return scm_find_files(base, hg_files, hg_dirs)

    def is_file_tracked(self, path: Path) -> bool:
        res = self.run_hg(["files", str(path)])
        return res.returncode == 0

    def get_dirty_tag_date(self) -> datetime.date | None:
        """Get the latest modification time of changed files in the working directory.

        Returns the date of the most recently modified file that has changes,
        or None if no files are changed or if an error occurs.
        """
        try:
            res = self.run_hg(["id", "-T", "{if(dirty, 1, 0)}"])
            if res.returncode != 0 or not bool(int(res.stdout)):
                return None

            status_res = self.run_hg(["status", "-m", "-a", "-r"])
            if status_res.returncode != 0:
                return None

            changed_files = []
            for line in status_res.stdout.strip().split("\n"):
                if line and len(line) > 2:
                    filepath = line[2:]
                    changed_files.append(filepath)

            return get_latest_file_mtime(changed_files, self.path)

        except Exception as e:
            log.debug("Failed to get dirty tag date: %s", e)

        return None


def parse(root: _t.PathT, config: Configuration) -> ScmVersion | None:
    hg_cmd = config.env.hg_command
    _require_command(hg_cmd)
    if os.path.exists(os.path.join(root, ".hg/git")):
        res = run_hg(
            ["path"], root, hg_command=hg_cmd, timeout=config.env.subprocess_timeout
        )
        if not res.returncode:
            for line in res.stdout.split("\n"):
                if line.startswith("default ="):
                    path = Path(line.split()[2])
                    if path.name.endswith(".git") or (path / ".git").exists():
                        from ._git import _git_parse_inner
                        from ._hg_git import GitWorkdirHgClient

                        wd_hggit = GitWorkdirHgClient.from_potential_worktree(
                            root, config
                        )
                        if wd_hggit:
                            return _git_parse_inner(config, wd_hggit)

    wd = HgWorkdir.from_potential_worktree(config.absolute_root, config)

    if wd is None:
        return None

    return wd.get_meta(config)


def archival_to_version(data: dict[str, str], config: Configuration) -> ScmVersion:
    log.debug("data %s", data)
    node = data.get("node", "")
    if node:
        node = "h" + node
    if "tag" in data:
        return meta(data["tag"], config=config)
    elif "latesttag" in data:
        return meta(
            data["latesttag"],
            distance=int(data["latesttagdistance"]),
            node=node,
            branch=data.get("branch"),
            config=config,
        )
    else:
        return meta(config.version_cls("0.0"), node=node, config=config)


def parse_archival(root: _t.PathT, config: Configuration) -> ScmVersion:
    archival = os.path.join(root, ".hg_archival.txt")
    data = data_from_mime(archival)
    return archival_to_version(data, config=config)
