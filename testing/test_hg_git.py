from __future__ import annotations

import pytest

from setuptools_scm import Configuration
from setuptools_scm._run_cmd import CommandNotFoundError
from setuptools_scm._run_cmd import has_command
from setuptools_scm._run_cmd import run
from setuptools_scm.hg import parse
from testing.wd_wrapper import WorkDir


@pytest.fixture(scope="module", autouse=True)
def _check_hg_git() -> None:
    if not has_command("hg", warn=False):
        pytest.skip("hg executable not found")

    res = run("hg debuginstall --template {pythonexe}", cwd=".")

    if res.returncode:
        skip_no_hggit = True
    else:
        res = run([res.stdout, "-c", "import hggit"], cwd=".")
        skip_no_hggit = bool(res.returncode)
    if skip_no_hggit:
        pytest.skip("hg-git not installed")


def test_base(repositories_hg_git: tuple[WorkDir, WorkDir]) -> None:
    wd, wd_git = repositories_hg_git

    assert wd_git.get_version() == "0.1.dev0+d20090213"
    assert wd.get_version() == "0.1.dev0+d20090213"

    wd_git.commit_testfile()
    version_git = wd_git.get_version()

    wd("hg pull -u")

    version = wd.get_version()

    assert version_git.startswith("0.1.dev1+g")
    assert version.startswith("0.1.dev1+g")

    assert not version_git.endswith("1-")
    assert not version.endswith("1-")

    wd_git("git tag v0.1")
    wd("hg pull -u")
    assert wd_git.get_version() == "0.1"
    assert wd.get_version() == "0.1"

    wd_git.write("test.txt", "test2")
    wd.write("test.txt", "test2")
    assert wd_git.get_version().startswith("0.2.dev0+g")
    assert wd.get_version().startswith("0.2.dev0+g")

    wd_git.commit_testfile()
    wd("hg pull")
    wd("hg up -C")
    assert wd_git.get_version().startswith("0.2.dev1+g")
    assert wd.get_version().startswith("0.2.dev1+g")

    wd_git("git tag version-0.2")
    wd("hg pull -u")
    assert wd_git.get_version().startswith("0.2")
    assert wd.get_version().startswith("0.2")

    wd_git.commit_testfile()
    wd_git("git tag version-0.2.post210+gbe48adfpost3+g0cc25f2")
    wd("hg pull -u")
    with pytest.warns(
        UserWarning, match="tag '.*' will be stripped of its suffix '.*'"
    ):
        assert wd_git.get_version().startswith("0.2")

    with pytest.warns(
        UserWarning, match="tag '.*' will be stripped of its suffix '.*'"
    ):
        assert wd.get_version().startswith("0.2")

    wd_git.commit_testfile()
    wd_git("git tag 17.33.0-rc")
    wd("hg pull -u")
    assert wd_git.get_version() == "17.33.0rc0"
    assert wd.get_version() == "17.33.0rc0"


def test_hg_gone(
    repositories_hg_git: tuple[WorkDir, WorkDir], monkeypatch: pytest.MonkeyPatch
) -> None:
    wd = repositories_hg_git[0]
    monkeypatch.setenv("PATH", str(wd.cwd / "not-existing"))
    config = Configuration()
    wd.write("pyproject.toml", "[tool.setuptools_scm]")
    with pytest.raises(CommandNotFoundError, match=r"hg"):
        parse(wd.cwd, config=config)

    assert wd.get_version(fallback_version="1.0") == "1.0"


def test_hg_command_from_env(
    repositories_hg_git: tuple[WorkDir, WorkDir],
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
    hg_exe: str,
) -> None:
    wd = repositories_hg_git[0]
    with monkeypatch.context() as m:
        m.setenv("SETUPTOOLS_SCM_HG_COMMAND", hg_exe)
        m.setenv("PATH", str(wd.cwd / "not-existing"))
        # No module reloading needed - runtime configuration works immediately
        wd.write("pyproject.toml", "[tool.setuptools_scm]")
        assert wd.get_version().startswith("0.1.dev0+")
