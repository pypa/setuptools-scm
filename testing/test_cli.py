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
