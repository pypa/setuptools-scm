from __future__ import annotations

import shutil
import subprocess

from pathlib import Path

import pytest

from setuptools_scm import Configuration
from setuptools_scm import dump_version
from setuptools_scm import get_version
from setuptools_scm._overrides import PRETEND_KEY
from setuptools_scm._run_cmd import has_command
from setuptools_scm.version import format_version
from setuptools_scm.version import guess_next_version
from setuptools_scm.version import meta
from setuptools_scm.version import tag_to_version

c = Configuration()


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("1.1", "1.2"),
        ("1.2.dev", "1.2"),
        ("1.1a2", "1.1a3"),
        pytest.param(
            "23.24.post2+deadbeef",
            "23.24.post3",
            marks=pytest.mark.filterwarnings(
                "ignore:.*will be stripped of its suffix.*:UserWarning"
            ),
        ),
    ],
)
def test_next_tag(tag: str, expected: str) -> None:
    version = meta(tag, config=c)
    assert guess_next_version(version) == expected


VERSIONS = {
    "exact": meta("1.1", distance=0, dirty=False, config=c),
    "dirty": meta("1.1", distance=0, dirty=True, config=c),
    "distance-clean": meta("1.1", distance=3, dirty=False, config=c),
    "distance-dirty": meta("1.1", distance=3, dirty=True, config=c),
}

# Versions with build metadata in the tag
VERSIONS_WITH_BUILD_METADATA = {
    "exact-build": meta("1.1+build.123", distance=0, dirty=False, config=c),
    "dirty-build": meta("1.1+build.123", distance=0, dirty=True, config=c),
    "distance-clean-build": meta("1.1+build.123", distance=3, dirty=False, config=c),
    "distance-dirty-build": meta("1.1+build.123", distance=3, dirty=True, config=c),
    "exact-ci": meta("2.0.0+ci.456", distance=0, dirty=False, config=c),
    "dirty-ci": meta("2.0.0+ci.456", distance=0, dirty=True, config=c),
    "distance-clean-ci": meta("2.0.0+ci.456", distance=2, dirty=False, config=c),
    "distance-dirty-ci": meta("2.0.0+ci.456", distance=2, dirty=True, config=c),
}


@pytest.mark.parametrize(
    ("version", "version_scheme", "local_scheme", "expected"),
    [
        ("exact", "guess-next-dev", "node-and-date", "1.1"),
        ("dirty", "guess-next-dev", "node-and-date", "1.2.dev0+d20090213"),
        ("dirty", "guess-next-dev", "no-local-version", "1.2.dev0"),
        ("distance-clean", "guess-next-dev", "node-and-date", "1.2.dev3"),
        ("distance-dirty", "guess-next-dev", "node-and-date", "1.2.dev3+d20090213"),
        ("exact", "post-release", "node-and-date", "1.1"),
        ("dirty", "post-release", "node-and-date", "1.1.post0+d20090213"),
        ("distance-clean", "post-release", "node-and-date", "1.1.post3"),
        ("distance-dirty", "post-release", "node-and-date", "1.1.post3+d20090213"),
    ],
)
def test_format_version(
    version: str, version_scheme: str, local_scheme: str, expected: str
) -> None:
    from dataclasses import replace

    scm_version = VERSIONS[version]
    configured_version = replace(
        scm_version,
        config=replace(
            scm_version.config, version_scheme=version_scheme, local_scheme=local_scheme
        ),
    )
    assert format_version(configured_version) == expected


@pytest.mark.parametrize(
    ("version", "version_scheme", "local_scheme", "expected"),
    [
        # Exact matches should preserve build metadata from tag
        ("exact-build", "guess-next-dev", "node-and-date", "1.1+build.123"),
        ("exact-build", "guess-next-dev", "no-local-version", "1.1+build.123"),
        ("exact-ci", "guess-next-dev", "node-and-date", "2.0.0+ci.456"),
        ("exact-ci", "guess-next-dev", "no-local-version", "2.0.0+ci.456"),
        # Dirty exact matches - version scheme treats dirty as non-exact, build metadata preserved
        (
            "dirty-build",
            "guess-next-dev",
            "node-and-date",
            "1.2.dev0+build.123.d20090213",
        ),
        ("dirty-build", "guess-next-dev", "no-local-version", "1.2.dev0+build.123"),
        ("dirty-ci", "guess-next-dev", "node-and-date", "2.0.1.dev0+ci.456.d20090213"),
        # Distance cases - build metadata should be preserved and combined with SCM data
        (
            "distance-clean-build",
            "guess-next-dev",
            "node-and-date",
            "1.2.dev3+build.123",
        ),
        (
            "distance-clean-build",
            "guess-next-dev",
            "no-local-version",
            "1.2.dev3+build.123",
        ),
        ("distance-clean-ci", "guess-next-dev", "node-and-date", "2.0.1.dev2+ci.456"),
        # Distance + dirty cases - build metadata should be preserved and combined with SCM data
        (
            "distance-dirty-build",
            "guess-next-dev",
            "node-and-date",
            "1.2.dev3+build.123.d20090213",
        ),
        (
            "distance-dirty-ci",
            "guess-next-dev",
            "node-and-date",
            "2.0.1.dev2+ci.456.d20090213",
        ),
        # Post-release scheme tests
        ("exact-build", "post-release", "node-and-date", "1.1+build.123"),
        (
            "dirty-build",
            "post-release",
            "node-and-date",
            "1.1.post0+build.123.d20090213",
        ),
        (
            "distance-clean-build",
            "post-release",
            "node-and-date",
            "1.1.post3+build.123",
        ),
        (
            "distance-dirty-build",
            "post-release",
            "node-and-date",
            "1.1.post3+build.123.d20090213",
        ),
    ],
)
def test_format_version_with_build_metadata(
    version: str, version_scheme: str, local_scheme: str, expected: str
) -> None:
    """Test format_version with tags that contain build metadata."""
    from dataclasses import replace

    from packaging.version import Version

    scm_version = VERSIONS_WITH_BUILD_METADATA[version]
    configured_version = replace(
        scm_version,
        config=replace(
            scm_version.config, version_scheme=version_scheme, local_scheme=local_scheme
        ),
    )
    result = format_version(configured_version)

    # Validate result is a valid PEP 440 version
    parsed = Version(result)
    assert str(parsed) == result, f"Result should be valid PEP 440: {result}"

    assert result == expected, f"Expected {expected}, got {result}"


def test_dump_version_doesnt_bail_on_value_error(tmp_path: Path) -> None:
    write_to = "VERSION"
    version = str(VERSIONS["exact"].tag)
    scm_version = meta(VERSIONS["exact"].tag, config=c)
    with pytest.raises(ValueError, match=r"^bad file format:"):
        dump_version(tmp_path, version, write_to, scm_version=scm_version)


@pytest.mark.parametrize(
    "version", ["1.0", "1.2.3.dev1+ge871260", "1.2.3.dev15+ge871260.d20180625"]
)
def test_dump_version_works_with_pretend(
    version: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(PRETEND_KEY, version)
    name = "VERSION.txt"
    target = tmp_path.joinpath(name)
    get_version(root=tmp_path, write_to=name)
    assert target.read_text(encoding="utf-8") == version


def test_dump_version_modern(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    version = "1.2.3"
    monkeypatch.setenv(PRETEND_KEY, version)
    name = "VERSION.txt"

    project = tmp_path.joinpath("project")
    target = project.joinpath(name)
    project.mkdir()

    get_version(root="..", relative_to=target, version_file=name)
    assert target.read_text(encoding="utf-8") == version


def dump_a_version(tmp_path: Path) -> None:
    from setuptools_scm._integration.dump_version import write_version_to_path

    version = "1.2.3"
    scm_version = meta(version, config=c)
    write_version_to_path(
        tmp_path / "VERSION.py", template=None, version=version, scm_version=scm_version
    )


def test_dump_version_on_old_python(tmp_path: Path) -> None:
    python37 = shutil.which("python3.7")
    if python37 is None:
        pytest.skip("python3.7 not found")
    dump_a_version(tmp_path)
    subprocess.run(
        [python37, "-c", "import VERSION;print(VERSION.version)"],
        cwd=tmp_path,
        check=True,
    )


def test_dump_version_mypy(tmp_path: Path) -> None:
    mypy = shutil.which("mypy")
    if mypy is None:
        pytest.skip("mypy not found")
    dump_a_version(tmp_path)
    subprocess.run(
        [mypy, "--python-version=3.8", "--strict", "VERSION.py"],
        cwd=tmp_path,
        check=True,
    )


def test_dump_version_flake8(tmp_path: Path) -> None:
    flake8 = shutil.which("flake8")
    if flake8 is None:
        pytest.skip("flake8 not found")
    dump_a_version(tmp_path)
    subprocess.run([flake8, "VERSION.py"], cwd=tmp_path, check=True)


def test_dump_version_ruff(tmp_path: Path) -> None:
    ruff = shutil.which("ruff")
    if ruff is None:
        pytest.skip("ruff not found")
    dump_a_version(tmp_path)
    subprocess.run([ruff, "check", "--no-fix", "VERSION.py"], cwd=tmp_path, check=True)


def test_has_command() -> None:
    with pytest.warns(RuntimeWarning, match="yadayada"):
        assert not has_command("yadayada_setuptools_aint_ne")


def test_has_command_logs_stderr(caplog: pytest.LogCaptureFixture) -> None:
    """
    If the name provided to has_command() exists as a command, but gives a non-zero
    return code, there should be a log message generated.
    """
    with pytest.warns(RuntimeWarning, match="ls"):
        has_command("ls", ["--a-flag-that-doesnt-exist-should-give-output-on-stderr"])
    found_it = False
    for record in caplog.records:
        if "returned non-zero. This is stderr" in record.message:
            found_it = True
    assert found_it, "Did not find expected log record for "


@pytest.mark.parametrize(
    ("tag", "expected_version"),
    [
        ("1.1", "1.1"),
        ("release-1.1", "1.1"),
        pytest.param("3.3.1-rc26", "3.3.1rc26", marks=pytest.mark.issue(266)),
    ],
)
def test_tag_to_version(tag: str, expected_version: str) -> None:
    version = str(tag_to_version(tag, c))
    assert version == expected_version
