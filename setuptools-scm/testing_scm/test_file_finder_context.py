"""The ``setuptools.file_finders`` hook must carry setuptools-scm settings.

setuptools calls file finders from ``walk_revctrl()`` during ``egg_info``,
after ``infer_version`` has returned and its ``ensure_context`` scope has
exited.  Without its own context the hook resolved env vars under the
``VCS_VERSIONING`` prefix only, so documented knobs such as
``SETUPTOOLS_SCM_SUBPROCESS_TIMEOUT`` were silently ignored (#1212).
"""

from __future__ import annotations

import os

from pathlib import Path

import pytest

from setuptools_scm._integration.file_finders import find_files
from vcs_versioning._backends._hg import _get_hg_command
from vcs_versioning._run_cmd import _get_timeout


@pytest.mark.issue(1212)
def test_setuptools_prefix_applies_in_finder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SETUPTOOLS_SCM_SUBPROCESS_TIMEOUT", "7")
    monkeypatch.setenv("SETUPTOOLS_SCM_HG_COMMAND", "not-really-hg")
    monkeypatch.chdir(tmp_path)

    seen: dict[str, object] = {}

    def record(path: object = "") -> list[str]:
        seen["timeout"] = _get_timeout(os.environ)
        seen["hg_command"] = _get_hg_command()
        return []

    monkeypatch.setattr("setuptools_scm._integration.file_finders._find_files", record)
    assert find_files(str(tmp_path)) == []

    assert seen == {"timeout": 7, "hg_command": "not-really-hg"}
