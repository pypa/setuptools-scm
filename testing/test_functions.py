from __future__ import annotations

from pathlib import Path

import pytest

from setuptools_scm import Configuration
from setuptools_scm import dump_version
from setuptools_scm import get_version
from setuptools_scm import PRETEND_KEY
from setuptools_scm._run_cmd import has_command
from setuptools_scm.version import format_version
from setuptools_scm.version import guess_next_version
from setuptools_scm.version import meta
from setuptools_scm.version import tag_to_version

c = Configuration()


@pytest.mark.parametrize(
    "tag, expected",
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


@pytest.mark.parametrize(
    "version,version_scheme, local_scheme,expected",
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
    scm_version = VERSIONS[version]
    assert (
        format_version(
            scm_version, version_scheme=version_scheme, local_scheme=local_scheme
        )
        == expected
    )


def test_dump_version_doesnt_bail_on_value_error(tmp_path: Path) -> None:
    write_to = "VERSION"
    version = str(VERSIONS["exact"].tag)
    with pytest.raises(ValueError, match="^bad file format:"):
        dump_version(tmp_path, version, write_to)


@pytest.mark.parametrize(
    "version", ["1.0", "1.2.3.dev1+ge871260", "1.2.3.dev15+ge871260.d20180625"]
)
def test_dump_version_works_with_pretend(
    version: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(PRETEND_KEY, version)
    target = tmp_path.joinpath("VERSION.txt")
    get_version(write_to=target)
    assert target.read_text() == version


def test_has_command() -> None:
    with pytest.warns(RuntimeWarning, match="yadayada"):
        assert not has_command("yadayada_setuptools_aint_ne")


@pytest.mark.parametrize(
    "tag, expected_version",
    [
        ("1.1", "1.1"),
        ("release-1.1", "1.1"),
        pytest.param("3.3.1-rc26", "3.3.1rc26", marks=pytest.mark.issue(266)),
    ],
)
def test_tag_to_version(tag: str, expected_version: str) -> None:
    version = str(tag_to_version(tag, c))
    assert version == expected_version
