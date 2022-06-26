from __future__ import annotations

import io
from contextlib import redirect_stdout

import pytest

from .conftest import DebugMode
from .test_git import wd as wd_fixture  # NOQA evil fixture reuse
from .wd_wrapper import WorkDir
from setuptools_scm._cli import main


PYPROJECT_TOML = "pyproject.toml"
PYPROJECT_SIMPLE = "[tool.setuptools_scm]"
PYPROJECT_ROOT = '[tool.setuptools_scm]\nroot=".."'


def get_output(args: list[str]) -> str:

    with redirect_stdout(io.StringIO()) as out:
        main(args)
    return out.getvalue()


def test_cli_find_pyproject(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch, debug_mode: DebugMode
) -> None:
    debug_mode.disable()
    wd.commit_testfile()
    wd.write(PYPROJECT_TOML, PYPROJECT_SIMPLE)
    monkeypatch.chdir(wd.cwd)

    out = get_output([])
    assert out.startswith("0.1.dev1+")

    with pytest.raises(SystemExit, match="no version found for"):
        get_output(["--root=.."])

    wd.write(PYPROJECT_TOML, PYPROJECT_ROOT)
    with pytest.raises(SystemExit, match="no version found for"):
        print(get_output(["-c", PYPROJECT_TOML]))

    with pytest.raises(SystemExit, match="no version found for"):

        get_output(["-c", PYPROJECT_TOML, "--root=.."])

    with pytest.warns(UserWarning, match="root .. is overridden by the cli arg ."):
        out = get_output(["-c", PYPROJECT_TOML, "--root=."])
    assert out.startswith("0.1.dev1+")
