"""GitHub Actions workflow annotations for configuration diagnostics."""

from __future__ import annotations

import dataclasses
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

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> GitHubActionsRun | None:
        if env.get("GITHUB_ACTIONS") != "true":
            return None
        sha = env.get("GITHUB_SHA")
        if not sha:
            return None
        workspace = env.get("GITHUB_WORKSPACE")
        return cls(sha=sha, workspace=Path(workspace) if workspace else None)

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
        """Emit a ``::warning`` workflow command at most once per process.

        Written to stderr so that commands printing machine-readable output
        on stdout stay parseable; the runner picks up both streams.
        """
        from ._backends._scm_workdir import _diagnostics_reported

        guard = f"github-annotation:{key}"
        if guard in _diagnostics_reported:
            return
        _diagnostics_reported.add(guard)

        properties = [f"title={_escape_property(title)}"]
        relative = self._workspace_relative(file) if file is not None else None
        if relative is not None:
            properties.insert(0, f"file={_escape_property(relative)}")
        print(
            f"::warning {','.join(properties)}::{_escape_data(message)}",
            file=sys.stderr,
        )
