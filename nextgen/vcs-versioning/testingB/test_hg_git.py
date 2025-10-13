from __future__ import annotations

import pytest

from vcs_versioning._run_cmd import CommandNotFoundError
from vcs_versioning._run_cmd import has_command
from vcs_versioning._run_cmd import run
from vcs_versioning.test_api import WorkDir

from setuptools_scm import Configuration
from setuptools_scm.hg import parse


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

    # Both should parse the same initial state
    wd_git.expect_parse(tag="0.0", distance=0, dirty=True)
    wd.expect_parse(tag="0.0", distance=0, dirty=True)

    # Also verify they produce the same formatted output
    assert wd_git.get_version() == wd.get_version()

    wd_git.commit_testfile()
    version_git = wd_git.get_version()

    wd("hg pull -u")
    version = wd.get_version()

    # Both should parse the same after commit
    wd_git.expect_parse(tag="0.0", distance=1, dirty=False, node_prefix="g")
    wd.expect_parse(tag="0.0", distance=1, dirty=False, node_prefix="g")

    # Check formatted output is similar (starts with same prefix)
    assert version_git.startswith("0.1.dev1+g")
    assert version.startswith("0.1.dev1+g")

    wd_git("git tag v0.1")
    wd("hg pull -u")

    # Both should recognize the tag
    wd_git.expect_parse(tag="0.1", distance=0, dirty=False, exact=True)
    wd.expect_parse(tag="0.1", distance=0, dirty=False, exact=True)

    wd_git.write("test.txt", "test2")
    wd.write("test.txt", "test2")
    # Both should be dirty
    wd_git.expect_parse(tag="0.1", distance=0, dirty=True)
    wd.expect_parse(tag="0.1", distance=0, dirty=True)

    wd_git.commit_testfile()
    wd("hg pull")
    wd("hg up -C")
    # Both should be at distance 1 from 0.1
    wd_git.expect_parse(tag="0.1", distance=1, dirty=False, node_prefix="g")
    wd.expect_parse(tag="0.1", distance=1, dirty=False, node_prefix="g")

    wd_git("git tag version-0.2")
    wd("hg pull -u")
    # Both should recognize the new tag
    wd_git.expect_parse(tag="0.2", distance=0, dirty=False, exact=True)
    wd.expect_parse(tag="0.2", distance=0, dirty=False, exact=True)

    wd_git.commit_testfile()
    wd_git("git tag version-0.2.post210+gbe48adfpost3+g0cc25f2")
    wd("hg pull -u")
    with pytest.warns(
        UserWarning, match="tag '.*' will be stripped of its suffix '.*'"
    ):
        wd_git.expect_parse(tag="0.2.post210", distance=0, dirty=False)

    with pytest.warns(
        UserWarning, match="tag '.*' will be stripped of its suffix '.*'"
    ):
        wd.expect_parse(tag="0.2.post210", distance=0, dirty=False)

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
