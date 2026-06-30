"""Tests for the scikit-build dynamic-metadata provider."""

from __future__ import annotations

from pathlib import Path

import pytest
from vcs_versioning import test_api
from vcs_versioning.dynamic_metadata import (
    dynamic_metadata,
    get_requires_for_dynamic_metadata,
)


def test_get_requires_for_dynamic_metadata() -> None:
    assert get_requires_for_dynamic_metadata({}) == ["vcs-versioning"]


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

    result = dynamic_metadata({"field": "version"}, {"name": "test-package"})

    assert result == {"version": "1.2.3"}


def test_field_defaults_to_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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

    # `field` omitted entirely still works.
    assert dynamic_metadata({}, {"name": "test-package"}) == {"version": "1.2.3"}


def test_non_version_field_rejected() -> None:
    with pytest.raises(ValueError, match="only supports the 'version' field"):
        dynamic_metadata({"field": "description"}, {})


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
    default = dynamic_metadata({"field": "version"}, {"name": "test-package"})
    assert "+" in default["version"]

    # Inline override is forwarded to infer_version_string and drops it.
    overridden = dynamic_metadata(
        {"field": "version", "local_scheme": "no-local-version"},
        {"name": "test-package"},
    )
    assert "+" not in overridden["version"]
    assert overridden["version"].startswith("1.0.1.dev1")
