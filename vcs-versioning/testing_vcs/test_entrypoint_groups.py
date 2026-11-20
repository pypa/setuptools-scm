from __future__ import annotations

from contextlib import nullcontext
from importlib.metadata import distribution
from pathlib import Path

import pytest
from vcs_versioning import Configuration
from vcs_versioning._file_finders import find_files
from vcs_versioning._get_version_impl import parse_version
from vcs_versioning._scm_version import ScmVersion, meta
from vcs_versioning._version_schemes import format_version

pytestmark = pytest.mark.issue(1400)


def install_plugin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, groups: str
) -> None:
    info = tmp_path / "sample_plugin-1.dist-info"
    info.mkdir()
    (info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: sample-plugin\nVersion: 1\n"
    )
    (info / "entry_points.txt").write_text(groups.replace("plugin:", __name__ + ":"))
    monkeypatch.syspath_prepend(str(tmp_path))


@pytest.mark.parametrize(
    "group",
    ["files_command", "files_command_fallback", "version_scheme", "local_scheme"],
)
def test_builtin_metadata_exposes_both_names(group: str) -> None:
    entries = distribution("vcs-versioning").entry_points
    old = {
        (ep.name, ep.value) for ep in entries if ep.group == f"setuptools_scm.{group}"
    }
    new = {
        (ep.name, ep.value) for ep in entries if ep.group == f"vcs_versioning.{group}"
    }
    assert new == old
    assert old


@pytest.mark.parametrize("prefix", ["vcs_versioning", "setuptools_scm"])
def test_named_scheme_plugins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, prefix: str
) -> None:
    groups = f"""
[{prefix}.version_scheme]
sample = vcs_versioning._version_schemes:only_version
[{prefix}.local_scheme]
sample = vcs_versioning._version_schemes:get_no_local_node
"""
    if prefix == "vcs_versioning":
        groups += """
[setuptools_scm.version_scheme]
sample = missing:lower_priority
[setuptools_scm.local_scheme]
sample = missing:lower_priority
"""
    install_plugin(tmp_path, monkeypatch, groups)
    config = Configuration(version_scheme="sample", local_scheme="sample")
    with (
        pytest.warns(DeprecationWarning, match="setuptools_scm")
        if prefix == "setuptools_scm"
        else nullcontext()
    ):
        assert format_version(meta("1.2", distance=1, config=config)) == "1.2"


def read_version(root: str, *, config: Configuration) -> ScmVersion:
    return meta((Path(root) / ".version").read_text(), config=config)


@pytest.mark.parametrize("group", ["parse_scm", "parse_scm_fallback"])
def test_parse_alias_is_used_after_workdir_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, group: str
) -> None:
    install_plugin(
        tmp_path,
        monkeypatch,
        f"[vcs_versioning.{group}]\n.version = plugin:read_version\n",
    )
    (tmp_path / ".version").write_text("2.4.6")
    config = Configuration(root=tmp_path, fallback_root=tmp_path)
    version = parse_version(config)
    assert version is not None
    assert str(version.tag) == "2.4.6"
    (tmp_path / "PKG-INFO").write_text(
        "Metadata-Version: 2.1\nName: sample\nVersion: 9.0\n"
    )
    version = parse_version(config)
    assert version is not None
    assert str(version.tag) == "9.0"


def empty_finder(path: str) -> list[str]:
    with (Path(path) / "calls").open("a") as fp:
        fp.write("called\n")
    return []


def other_finder(path: str) -> list[str]:
    return ["tracked.txt"]


@pytest.mark.parametrize("group", ["files_command", "files_command_fallback"])
def test_distinct_finders_at_same_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, group: str
) -> None:
    install_plugin(
        tmp_path,
        monkeypatch,
        f"""
[vcs_versioning.{group}]
.both = plugin:empty_finder
.marker = plugin:empty_finder
[setuptools_scm.{group}]
.both = plugin:empty_finder
.marker = plugin:other_finder
""",
    )
    (tmp_path / ".marker").touch()
    (tmp_path / ".both").touch()
    with pytest.warns(DeprecationWarning, match="setuptools_scm"):
        assert find_files(tmp_path) == ["tracked.txt"]
    assert (tmp_path / "calls").read_text().splitlines() == ["called", "called"]


def test_nearest_primary_finder_wins_over_parent_and_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_plugin(
        tmp_path,
        monkeypatch,
        """
[vcs_versioning.files_command]
.outer = missing:outer_finder
[setuptools_scm.files_command]
.inner = plugin:other_finder
[vcs_versioning.files_command_fallback]
.inner = missing:fallback_finder
""",
    )
    (tmp_path / ".outer").touch()
    inner = tmp_path / "inner"
    inner.mkdir()
    (inner / ".inner").touch()
    with pytest.warns(DeprecationWarning, match="setuptools_scm.files_command"):
        assert find_files(inner) == ["tracked.txt"]
