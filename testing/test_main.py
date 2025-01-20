from __future__ import annotations

import sys
import textwrap

from pathlib import Path

import pytest

from .wd_wrapper import WorkDir


def test_main() -> None:
    mainfile = Path(__file__).parent.parent.joinpath(
        "src", "setuptools_scm", "__main__.py"
    )
    ns = {"__package__": "setuptools_scm"}

    code = compile(mainfile.read_text(encoding="utf-8"), "__main__.py", "exec")
    exec(code, ns)


@pytest.fixture
def repo(wd: WorkDir) -> WorkDir:
    wd("git init")
    wd("git config user.email user@host")
    wd("git config user.name user")
    wd.add_command = "git add ."
    wd.commit_command = "git commit -m test-{reason}"

    wd.write("README.rst", "My example")
    wd.add_and_commit()
    wd("git tag v0.1.0")

    wd.write("file.txt", "file.txt")
    wd.add_and_commit()

    return wd


def test_repo_with_config(repo: WorkDir) -> None:
    pyproject = """\
    [tool.setuptools_scm]
    version_scheme = "no-guess-dev"

    [project]
    name = "example"
    """
    repo.write("pyproject.toml", textwrap.dedent(pyproject))
    repo.add_and_commit()
    res = repo([sys.executable, "-m", "setuptools_scm"])
    assert res.startswith("0.1.0.post1.dev2")


def test_repo_without_config(repo: WorkDir) -> None:
    res = repo([sys.executable, "-m", "setuptools_scm"])
    assert res.startswith("0.1.1.dev1")


def test_repo_with_pyproject_missing_setuptools_scm(repo: WorkDir) -> None:
    pyproject = """\
    [project]
    name = "example"
    """
    repo.write("pyproject.toml", textwrap.dedent(pyproject))
    repo.add_and_commit()
    res = repo([sys.executable, "-m", "setuptools_scm"])
    assert res.startswith("0.1.1.dev2")
