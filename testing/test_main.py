import os.path
import sys
import textwrap

import pytest


def test_main():
    mainfile = os.path.join(
        os.path.dirname(__file__), "..", "src", "setuptools_scm", "__main__.py"
    )
    with open(mainfile) as f:
        code = compile(f.read(), "__main__.py", "exec")
        exec(code)


@pytest.fixture
def repo(wd):
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


def test_repo_with_config(repo):
    pyproject = """\
    [tool.setuptools_scm]
    version_scheme = "no-guess-dev"

    [project]
    name = "example"
    """
    repo.write("pyproject.toml", textwrap.dedent(pyproject))
    repo.add_and_commit()
    res = repo((sys.executable, "-m", "setuptools_scm"))
    assert res.startswith("0.1.0.post1.dev2")


def test_repo_without_config(repo):
    res = repo((sys.executable, "-m", "setuptools_scm"))
    assert res.startswith("0.1.1.dev1")


def test_repo_with_pyproject_missing_setuptools_scm(repo):
    pyproject = """\
    [project]
    name = "example"
    """
    repo.write("pyproject.toml", textwrap.dedent(pyproject))
    repo.add_and_commit()
    res = repo((sys.executable, "-m", "setuptools_scm"))
    assert res.startswith("0.1.1.dev2")
