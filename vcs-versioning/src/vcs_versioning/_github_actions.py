"""GitHub Actions workflow annotations for configuration diagnostics."""

from __future__ import annotations

import dataclasses
import hashlib
import os
import sys
from collections.abc import Mapping
from pathlib import Path


def _escape_data(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_property(value: str) -> str:
    return _escape_data(value).replace(":", "%3A").replace(",", "%2C")


@dataclasses.dataclass(frozen=True)
class GitHubActionsRun:
    """The workflow run this process executes in.

    ``sha`` is the commit the run is about.  Diagnostics about the project's
    own setup are annotated only on a checkout of exactly that commit, so a
    run that installs some other repository from git, or builds throwaway
    test repositories, does not get annotations it cannot act on.
    """

    sha: str
    workspace: Path | None
    runner_temp: Path | None = None

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> GitHubActionsRun | None:
        if env.get("GITHUB_ACTIONS") != "true":
            return None
        sha = env.get("GITHUB_SHA")
        if not sha:
            return None
        workspace = env.get("GITHUB_WORKSPACE")
        runner_temp = env.get("RUNNER_TEMP")
        return cls(
            sha=sha,
            workspace=Path(workspace) if workspace else None,
            runner_temp=Path(runner_temp) if runner_temp else None,
        )

    def _claim_for_job(self, key: str) -> bool:
        """Whether no other process in this job has emitted *key* yet.

        A build frontend runs the backend in several processes, and each
        would annotate once; GitHub shows every copy.  ``RUNNER_TEMP`` is
        emptied between jobs, so a marker there limits it to one per job.
        """
        if self.runner_temp is None:
            return True
        digest = hashlib.sha256(f"{self.sha}\0{key}".encode()).hexdigest()
        marker = self.runner_temp / "vcs-versioning-annotations" / digest
        try:
            marker.parent.mkdir(parents=True, exist_ok=True)
            # O_EXCL: concurrent backend processes must not both win.
            os.close(os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        except FileExistsError:
            return False
        except OSError:
            return True
        return True

    def _workspace_relative(self, path: Path) -> str | None:
        if self.workspace is None or not path.exists():
            return None
        try:
            return path.resolve().relative_to(self.workspace.resolve()).as_posix()
        except ValueError:
            return None

    def warn_once(
        self, key: str, *, title: str, message: str, file: Path | None = None
    ) -> None:
        """Emit a ``::warning`` workflow command at most once per job.

        Written to stderr so that commands printing machine-readable output
        on stdout stay parseable; the runner picks up both streams.
        """
        from ._backends._scm_workdir import _diagnostics_reported

        guard = f"github-annotation:{key}"
        if guard in _diagnostics_reported:
            return
        _diagnostics_reported.add(guard)
        if not self._claim_for_job(key):
            return

        properties = [f"title={_escape_property(title)}"]
        relative = self._workspace_relative(file) if file is not None else None
        if relative is not None:
            properties.insert(0, f"file={_escape_property(relative)}")
        print(
            f"::warning {','.join(properties)}::{_escape_data(message)}",
            file=sys.stderr,
        )
