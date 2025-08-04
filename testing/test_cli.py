from __future__ import annotations

import io

from contextlib import redirect_stdout

import pytest

from setuptools_scm._cli import main

from .conftest import DebugMode
from .test_git import wd as wd_fixture  # noqa: F401 (evil fixture reuse)
from .wd_wrapper import WorkDir

PYPROJECT_TOML = "pyproject.toml"
PYPROJECT_SIMPLE = "[tool.setuptools_scm]"
PYPROJECT_ROOT = '[tool.setuptools_scm]\nroot=".."'


def get_output(args: list[str]) -> str:
    with redirect_stdout(io.StringIO()) as out:
        main(args)
    return out.getvalue()


warns_cli_root_override = pytest.warns(
    UserWarning, match="root .. is overridden by the cli arg .*"
)

exits_with_not_found = pytest.raises(SystemExit, match="no version found for")


def test_cli_find_pyproject(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch, debug_mode: DebugMode
) -> None:
    wd.commit_testfile()
    wd.write(PYPROJECT_TOML, PYPROJECT_SIMPLE)
    monkeypatch.chdir(wd.cwd)
    out = get_output([])
    assert out.startswith("0.1.dev1+")

    with exits_with_not_found:
        get_output(["--root=.."])

    wd.write(PYPROJECT_TOML, PYPROJECT_ROOT)
    with exits_with_not_found:
        print(get_output(["-c", PYPROJECT_TOML]))

    with warns_cli_root_override, exits_with_not_found:
        get_output(["-c", PYPROJECT_TOML, "--root=.."])

    with warns_cli_root_override:
        out = get_output(["-c", PYPROJECT_TOML, "--root=."])
    assert out.startswith("0.1.dev1+")


def test_cli_force_version_files(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch, debug_mode: DebugMode
) -> None:
    debug_mode.disable()
    wd.commit_testfile()
    wd.write(
        PYPROJECT_TOML,
        """
[project]
name = "test"
[tool.setuptools_scm]
version_file = "ver.py"
""",
    )
    monkeypatch.chdir(wd.cwd)

    version_file = wd.cwd.joinpath("ver.py")
    assert not version_file.exists()

    get_output([])
    assert not version_file.exists()

    output = get_output(["--force-write-version-files"])
    assert version_file.exists()

    assert output[:5] in version_file.read_text("utf-8")


def test_cli_create_archival_file_stable(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test creating stable .git_archival.txt file."""
    wd.commit_testfile()
    wd.write(PYPROJECT_TOML, PYPROJECT_SIMPLE)
    monkeypatch.chdir(wd.cwd)

    archival_file = wd.cwd / ".git_archival.txt"
    assert not archival_file.exists()

    result = main(["create-archival-file", "--stable"])
    assert result == 0
    assert archival_file.exists()

    content = archival_file.read_text("utf-8")
    expected_lines = [
        "node: $Format:%H$",
        "node-date: $Format:%cI$",
        "describe-name: $Format:%(describe:tags=true,match=*[0-9]*)$",
    ]
    for line in expected_lines:
        assert line in content

    # Stable version should not contain ref-names
    assert "ref-names" not in content


def test_cli_create_archival_file_full(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test creating full .git_archival.txt file with branch information."""
    wd.commit_testfile()
    wd.write(PYPROJECT_TOML, PYPROJECT_SIMPLE)
    monkeypatch.chdir(wd.cwd)

    archival_file = wd.cwd / ".git_archival.txt"
    assert not archival_file.exists()

    result = main(["create-archival-file", "--full"])
    assert result == 0
    assert archival_file.exists()

    content = archival_file.read_text("utf-8")
    expected_lines = [
        "node: $Format:%H$",
        "node-date: $Format:%cI$",
        "describe-name: $Format:%(describe:tags=true,match=*[0-9]*)$",
        "ref-names: $Format:%D$",
    ]
    for line in expected_lines:
        assert line in content

    # Full version should contain warning comment
    assert "WARNING" in content
    assert "unstable" in content


def test_cli_create_archival_file_exists_no_force(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that existing .git_archival.txt file prevents creation without --force."""
    wd.commit_testfile()
    wd.write(PYPROJECT_TOML, PYPROJECT_SIMPLE)
    monkeypatch.chdir(wd.cwd)

    archival_file = wd.cwd / ".git_archival.txt"
    archival_file.write_text("existing content", encoding="utf-8")

    # Should fail without --force
    result = main(["create-archival-file", "--stable"])
    assert result == 1

    # Content should be unchanged
    assert archival_file.read_text("utf-8") == "existing content"


def test_cli_create_archival_file_exists_with_force(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that --force overwrites existing .git_archival.txt file."""
    wd.commit_testfile()
    wd.write(PYPROJECT_TOML, PYPROJECT_SIMPLE)
    monkeypatch.chdir(wd.cwd)

    archival_file = wd.cwd / ".git_archival.txt"
    archival_file.write_text("existing content", encoding="utf-8")

    # Should succeed with --force
    result = main(["create-archival-file", "--stable", "--force"])
    assert result == 0

    # Content should be updated
    content = archival_file.read_text("utf-8")
    assert "existing content" not in content
    assert "node: $Format:%H$" in content


def test_cli_create_archival_file_requires_stable_or_full(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that create-archival-file requires either --stable or --full."""
    wd.commit_testfile()
    wd.write(PYPROJECT_TOML, PYPROJECT_SIMPLE)
    monkeypatch.chdir(wd.cwd)

    # Should fail without --stable or --full
    with pytest.raises(SystemExit):
        main(["create-archival-file"])


def test_cli_create_archival_file_mutually_exclusive(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that --stable and --full are mutually exclusive."""
    wd.commit_testfile()
    wd.write(PYPROJECT_TOML, PYPROJECT_SIMPLE)
    monkeypatch.chdir(wd.cwd)

    # Should fail with both --stable and --full
    with pytest.raises(SystemExit):
        main(["create-archival-file", "--stable", "--full"])


def test_cli_create_archival_file_existing_gitattributes(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test behavior when .gitattributes already has export-subst configuration."""
    wd.commit_testfile()
    wd.write(PYPROJECT_TOML, PYPROJECT_SIMPLE)
    monkeypatch.chdir(wd.cwd)

    # Create .gitattributes with export-subst configuration
    gitattributes_file = wd.cwd / ".gitattributes"
    gitattributes_file.write_text(".git_archival.txt  export-subst\n", encoding="utf-8")

    result = main(["create-archival-file", "--stable"])
    assert result == 0

    archival_file = wd.cwd / ".git_archival.txt"
    assert archival_file.exists()


def test_cli_create_archival_file_no_gitattributes(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test behavior when .gitattributes doesn't exist or lacks export-subst."""
    wd.commit_testfile()
    wd.write(PYPROJECT_TOML, PYPROJECT_SIMPLE)
    monkeypatch.chdir(wd.cwd)

    result = main(["create-archival-file", "--stable"])
    assert result == 0

    archival_file = wd.cwd / ".git_archival.txt"
    assert archival_file.exists()
