"""Tests for the scikit-build dynamic-metadata provider."""

from __future__ import annotations

from pathlib import Path

import pytest
from vcs_versioning import dynamic_metadata, test_api


def test_pretend_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "test-package"
dynamic = ["version"]

[tool.vcs-versioning]
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VCS_VERSIONING_PRETEND_VERSION_FOR_TEST_PACKAGE", "1.2.3")

    assert dynamic_metadata({}, {"name": "test-package"}) == {"version": "1.2.3"}


def test_inline_override_drops_local_segment(
    wd: test_api.WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    wd.setup_git(monkeypatch)
    wd.create_basic_pyproject_toml(name="test-package")
    wd.add_and_commit()
    wd.create_tag("1.0.0")
    wd.commit_testfile()
    monkeypatch.chdir(wd.cwd)

    # Default local scheme adds a +g<node> local segment.
    default = dynamic_metadata({}, {"name": "test-package"})
    assert "+" in default["version"]

    # Inline settings are forwarded to infer_version_string as overrides.
    overridden = dynamic_metadata(
        {"local_scheme": "no-local-version"},
        {"name": "test-package"},
    )
    assert "+" not in overridden["version"]
    assert overridden["version"].startswith("1.0.1.dev1")
