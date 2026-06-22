"""Single smart-probe factory for jj/git/hg/hg-git VCS discovery.

Registered as ``hg-git`` in the ``vcs_versioning.discover_workdir`` entry
point group.  Examines the directory for ``.jj``, ``.hg``, ``.hg/git``,
and ``.git`` markers and returns the correct ScmWorkdir subclass.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .._config import Configuration
from .._run_cmd import has_command
from ._scm_workdir import ScmWorkdir

log = logging.getLogger(__name__)


def discover(path: Path, *, config: Configuration) -> ScmWorkdir | None:
    """Probe *path* for jj, git, hg, or hg-git markers.

    Returns:
        - ``JjWorkdir`` for Jujutsu (``.jj``)
        - ``GitWorkdirHgClient`` for hg-git hybrids (``.hg`` + ``.hg/git``)
        - ``HgWorkdir`` for plain mercurial (``.hg`` only, or ``.hg`` + ``.git`` without ``.hg/git``)
        - ``GitWorkdir`` for plain git (``.git`` only)
        - ``None`` when no VCS markers found

    Raises:
        LookupError: when ``.jj/`` is present but ``jj`` is not on PATH
    """
    has_jj = (path / ".jj").is_dir()
    has_hg = (path / ".hg").is_dir()
    has_git = (path / ".git").exists()
    has_hg_git = has_hg and (path / ".hg" / "git").is_dir()

    if has_jj:
        if not has_command("jj", args=["version"], warn=False):
            raise LookupError(
                f"Jujutsu (jj) repository detected at {path} but the 'jj' "
                "command is not available. Install jj "
                "(https://jj-vcs.dev/docs/install) or remove the .jj directory "
                "if this is not a jj-managed workspace."
            )
        log.debug("jujutsu detected at %s", path)
        from ._jj import JjWorkdir

        return JjWorkdir.from_potential_worktree(path, config)

    if has_hg and has_hg_git:
        log.debug("hg-git hybrid detected at %s", path)
        from ._hg_git import GitWorkdirHgClient

        return GitWorkdirHgClient.from_potential_worktree(path, config)

    if has_hg:
        log.debug("mercurial detected at %s", path)
        from ._hg import HgWorkdir

        return HgWorkdir.from_potential_worktree(path, config)

    if has_git:
        log.debug("git detected at %s", path)
        from ._git import GitWorkdir

        return GitWorkdir.from_potential_worktree(path, config)

    return None
