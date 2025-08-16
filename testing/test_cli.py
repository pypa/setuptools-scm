from __future__ import annotations

import io

from contextlib import redirect_stdout

import pytest

from setuptools_scm._cli import main
from setuptools_scm._integration.pyproject_reading import PyProjectData

from .conftest import DebugMode
from .wd_wrapper import WorkDir


@pytest.fixture
def wd(wd: WorkDir, monkeypatch: pytest.MonkeyPatch, debug_mode: DebugMode) -> WorkDir:
    """Set up git for CLI tests."""
    debug_mode.disable()
    wd.setup_git(monkeypatch)
    debug_mode.enable()
    return wd


PYPROJECT_TOML = "pyproject.toml"
PYPROJECT_SIMPLE = "[tool.setuptools_scm]"
PYPROJECT_ROOT = '[tool.setuptools_scm]\nroot=".."'

# PyProjectData constants for testing
PYPROJECT_DATA_SIMPLE = PyProjectData.for_testing(section_present=True)
PYPROJECT_DATA_WITH_PROJECT = PyProjectData.for_testing(
    section_present=True, project_present=True, project_name="test"
)


def _create_version_file_pyproject_data() -> PyProjectData:
    """Create PyProjectData with version_file configuration for testing."""
    data = PyProjectData.for_testing(
        section_present=True, project_present=True, project_name="test"
    )
    data.section["version_file"] = "ver.py"
    return data


def get_output(
    args: list[str], *, _given_pyproject_data: PyProjectData | None = None
) -> str:
    with redirect_stdout(io.StringIO()) as out:
        main(args, _given_pyproject_data=_given_pyproject_data)
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
    monkeypatch.chdir(wd.cwd)

    version_file = wd.cwd.joinpath("ver.py")
    assert not version_file.exists()

    # Create pyproject data with version_file configuration
    pyproject_data = _create_version_file_pyproject_data()

    get_output([], _given_pyproject_data=pyproject_data)
    assert not version_file.exists()

    output = get_output(
        ["--force-write-version-files"], _given_pyproject_data=pyproject_data
    )
    assert version_file.exists()

    assert output[:5] in version_file.read_text("utf-8")


def test_cli_create_archival_file_stable(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test creating stable .git_archival.txt file."""
    wd.commit_testfile()
    monkeypatch.chdir(wd.cwd)

    archival_file = wd.cwd / ".git_archival.txt"
    assert not archival_file.exists()

    # Use injected pyproject data instead of creating a file
    pyproject_data = PYPROJECT_DATA_SIMPLE
    result = main(
        ["create-archival-file", "--stable"], _given_pyproject_data=pyproject_data
    )
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
    monkeypatch.chdir(wd.cwd)

    archival_file = wd.cwd / ".git_archival.txt"
    assert not archival_file.exists()

    # Use injected pyproject data instead of creating a file
    pyproject_data = PYPROJECT_DATA_SIMPLE
    result = main(
        ["create-archival-file", "--full"], _given_pyproject_data=pyproject_data
    )
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
    wd.setup_git(monkeypatch)
    wd.commit_testfile()
    monkeypatch.chdir(wd.cwd)

    archival_file = wd.cwd / ".git_archival.txt"
    archival_file.write_text("existing content", encoding="utf-8")

    # Should fail without --force
    pyproject_data = PYPROJECT_DATA_SIMPLE
    result = main(
        ["create-archival-file", "--stable"], _given_pyproject_data=pyproject_data
    )
    assert result == 1

    # Content should be unchanged
    assert archival_file.read_text("utf-8") == "existing content"


def test_cli_create_archival_file_exists_with_force(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that --force overwrites existing .git_archival.txt file."""
    wd.setup_git(monkeypatch)
    wd.commit_testfile()
    monkeypatch.chdir(wd.cwd)

    archival_file = wd.cwd / ".git_archival.txt"
    archival_file.write_text("existing content", encoding="utf-8")

    # Should succeed with --force
    pyproject_data = PYPROJECT_DATA_SIMPLE
    result = main(
        ["create-archival-file", "--stable", "--force"],
        _given_pyproject_data=pyproject_data,
    )
    assert result == 0

    # Content should be updated
    content = archival_file.read_text("utf-8")
    assert "existing content" not in content
    assert "node: $Format:%H$" in content


def test_cli_create_archival_file_requires_stable_or_full(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that create-archival-file requires either --stable or --full."""
    wd.setup_git(monkeypatch)
    wd.commit_testfile()
    monkeypatch.chdir(wd.cwd)

    # Should fail without --stable or --full
    pyproject_data = PYPROJECT_DATA_SIMPLE
    with pytest.raises(SystemExit):
        main(["create-archival-file"], _given_pyproject_data=pyproject_data)


def test_cli_create_archival_file_mutually_exclusive(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that --stable and --full are mutually exclusive."""
    wd.setup_git(monkeypatch)
    wd.commit_testfile()
    monkeypatch.chdir(wd.cwd)

    # Should fail with both --stable and --full
    pyproject_data = PYPROJECT_DATA_SIMPLE
    with pytest.raises(SystemExit):
        main(
            ["create-archival-file", "--stable", "--full"],
            _given_pyproject_data=pyproject_data,
        )


def test_cli_create_archival_file_existing_gitattributes(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test behavior when .gitattributes already has export-subst configuration."""
    wd.commit_testfile()
    monkeypatch.chdir(wd.cwd)

    # Create .gitattributes with export-subst configuration
    gitattributes_file = wd.cwd / ".gitattributes"
    gitattributes_file.write_text(".git_archival.txt  export-subst\n", encoding="utf-8")

    pyproject_data = PYPROJECT_DATA_SIMPLE
    result = main(
        ["create-archival-file", "--stable"], _given_pyproject_data=pyproject_data
    )
    assert result == 0

    archival_file = wd.cwd / ".git_archival.txt"
    assert archival_file.exists()


def test_cli_create_archival_file_no_gitattributes(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test behavior when .gitattributes doesn't exist or lacks export-subst."""
    wd.commit_testfile()
    monkeypatch.chdir(wd.cwd)

    pyproject_data = PYPROJECT_DATA_SIMPLE
    result = main(
        ["create-archival-file", "--stable"], _given_pyproject_data=pyproject_data
    )
    assert result == 0

    archival_file = wd.cwd / ".git_archival.txt"
    assert archival_file.exists()
