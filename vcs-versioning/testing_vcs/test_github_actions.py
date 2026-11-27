from __future__ import annotations

from pathlib import Path

import pytest
from vcs_versioning import Configuration
from vcs_versioning._github_actions import GitHubActionsRun
from vcs_versioning.test_api import DebugMode, WorkDir

ARCHIVAL = "node: $Format:%H$\ndescribe-name: $Format:%(describe:tags=true)$\n"
ANNOTATION = "::warning "


@pytest.fixture
def wd(wd: WorkDir, monkeypatch: pytest.MonkeyPatch, debug_mode: DebugMode) -> WorkDir:
    debug_mode.disable()
    wd.setup_git(monkeypatch)
    debug_mode.enable()
    return wd


def head(wd: WorkDir) -> str:
    return wd("git rev-parse HEAD").strip()


def run_on(wd: WorkDir, monkeypatch: pytest.MonkeyPatch, sha: str) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_SHA", sha)
    monkeypatch.setenv("GITHUB_WORKSPACE", str(wd.cwd))


def commit_archival(wd: WorkDir, gitattributes: str | None) -> None:
    wd.write(".git_archival.txt", ARCHIVAL)
    if gitattributes is not None:
        wd.write(".gitattributes", gitattributes)
    wd.add_and_commit()
    wd("git tag v1.0")


def emitted_annotations(capsys: pytest.CaptureFixture[str]) -> list[str]:
    return [
        line
        for line in capsys.readouterr().err.splitlines()
        if line.startswith(ANNOTATION)
    ]


@pytest.mark.issue(1435)
@pytest.mark.parametrize(
    ("gitattributes", "expected_prefix"),
    [
        pytest.param(None, "::warning title=", id="no-gitattributes"),
        pytest.param(
            "*.txt export-subst\n.git_archival.txt -export-subst\n",
            "::warning file=.gitattributes,title=",
            id="unset-by-later-pattern",
        ),
        pytest.param("*.md text\n", "::warning file=.gitattributes,title=", id="other"),
    ],
)
def test_workflow_checkout_without_export_subst_is_annotated_once(
    wd: WorkDir,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    gitattributes: str | None,
    expected_prefix: str,
) -> None:
    commit_archival(wd, gitattributes)
    run_on(wd, monkeypatch, head(wd))

    assert wd.get_version() == "1.0"
    assert wd.get_version() == "1.0"

    [annotation] = emitted_annotations(capsys)
    assert annotation.startswith(expected_prefix)
    assert "Add '.git_archival.txt export-subst' to .gitattributes" in annotation


@pytest.mark.issue(1435)
@pytest.mark.parametrize(
    "gitattributes",
    [".git_archival.txt export-subst\n", "*.txt export-subst\n"],
)
def test_workflow_checkout_with_export_subst_is_silent(
    wd: WorkDir,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    gitattributes: str,
) -> None:
    commit_archival(wd, gitattributes)
    run_on(wd, monkeypatch, head(wd))

    assert wd.get_version() == "1.0"
    assert emitted_annotations(capsys) == []


@pytest.mark.issue(1435)
def test_checkout_of_another_commit_is_silent(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A git dependency installed in someone else's workflow is not theirs to fix."""
    commit_archival(wd, None)
    run_on(wd, monkeypatch, "0" * 40)

    assert wd.get_version() == "1.0"
    assert emitted_annotations(capsys) == []


@pytest.mark.issue(1435)
def test_outside_github_actions_is_silent(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    commit_archival(wd, None)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setenv("GITHUB_SHA", head(wd))

    assert wd.get_version() == "1.0"
    assert emitted_annotations(capsys) == []


@pytest.mark.issue(1435)
def test_subdirectory_project_archival_is_checked(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Monorepo projects keep their .git_archival.txt next to pyproject.toml."""
    wd.write("pkg/pyproject.toml", "[project]\nname = 'pkg'\n")
    wd.write("pkg/.git_archival.txt", ARCHIVAL)
    wd.write(".gitattributes", "*.md text\n")
    wd.add_and_commit()
    wd("git tag v1.0")
    run_on(wd, monkeypatch, head(wd))

    from vcs_versioning._get_version_impl import get_version

    pyproject = wd.cwd / "pkg" / "pyproject.toml"
    assert get_version(root="..", relative_to=str(pyproject)) == "1.0"

    [annotation] = emitted_annotations(capsys)
    assert "Add 'pkg/.git_archival.txt export-subst'" in annotation


@pytest.mark.issue(1435)
def test_version_file_outside_root_is_annotated_on_workflow_checkout(
    wd: WorkDir, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from vcs_versioning._get_version_impl import _warn_if_tracked

    wd.commit_testfile()
    run_on(wd, monkeypatch, head(wd))
    config = Configuration(root=str(wd.cwd))

    with pytest.warns(UserWarning, match="resolves outside of"):
        assert not _warn_if_tracked(Path("../outside.py"), wd.cwd, config)

    [annotation] = emitted_annotations(capsys)
    assert annotation.startswith("::warning title=version file is outside")


def test_workflow_command_values_are_escaped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Unescaped newlines or colons would end the command or the property early."""
    (tmp_path / "a,b:c").write_text("")
    run = GitHubActionsRun(sha="0" * 40, workspace=tmp_path)

    run.warn_once("k", title="t: 1, 2", message="100%\nnext", file=tmp_path / "a,b:c")
    run.warn_once("k", title="again", message="again")

    assert capsys.readouterr().err == (
        "::warning file=a%2Cb%3Ac,title=t%3A 1%2C 2::100%25%0Anext\n"
    )


@pytest.mark.parametrize(
    "env",
    [
        {"GITHUB_SHA": "abc"},
        {"GITHUB_ACTIONS": "false", "GITHUB_SHA": "abc"},
        {"GITHUB_ACTIONS": "true"},
    ],
)
def test_run_is_only_detected_with_actions_and_sha(env: dict[str, str]) -> None:
    assert GitHubActionsRun.from_env(env) is None
