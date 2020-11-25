import pytest
import sys
import pkg_resources
from setuptools_scm import dump_version, get_version, PRETEND_KEY
from setuptools_scm.version import (
    guess_next_version,
    meta,
    format_version,
    tag_to_version,
)

from setuptools_scm.config import Configuration
from setuptools_scm.utils import has_command

PY3 = sys.version_info > (2,)


@pytest.mark.parametrize(
    "tag, expected",
    [
        ("1.1", "1.2"),
        ("1.2.dev", "1.2"),
        ("1.1a2", "1.1a3"),
        ("23.24.post2+deadbeef", "23.24.post3"),
    ],
)
def test_next_tag(tag, expected):
    version = pkg_resources.parse_version(tag)
    assert guess_next_version(version) == expected


c = Configuration()

VERSIONS = {
    "exact": meta("1.1", distance=None, dirty=False, config=c),
    "zerodistance": meta("1.1", distance=0, dirty=False, config=c),
    "dirty": meta("1.1", distance=None, dirty=True, config=c),
    "distance": meta("1.1", distance=3, dirty=False, config=c),
    "distancedirty": meta("1.1", distance=3, dirty=True, config=c),
}


@pytest.mark.parametrize(
    "version,scheme,expected",
    [
        ("exact", "guess-next-dev node-and-date", "1.1"),
        ("zerodistance", "guess-next-dev node-and-date", "1.2.dev0"),
        ("zerodistance", "guess-next-dev no-local-version", "1.2.dev0"),
        ("dirty", "guess-next-dev node-and-date", "1.2.dev0+d20090213"),
        ("dirty", "guess-next-dev no-local-version", "1.2.dev0"),
        ("distance", "guess-next-dev node-and-date", "1.2.dev3"),
        ("distancedirty", "guess-next-dev node-and-date", "1.2.dev3+d20090213"),
        ("distancedirty", "guess-next-dev no-local-version", "1.2.dev3"),
        ("exact", "post-release node-and-date", "1.1"),
        ("zerodistance", "post-release node-and-date", "1.1.post0"),
        ("dirty", "post-release node-and-date", "1.1.post0+d20090213"),
        ("distance", "post-release node-and-date", "1.1.post3"),
        ("distancedirty", "post-release node-and-date", "1.1.post3+d20090213"),
    ],
)
def test_format_version(version, scheme, expected):
    version = VERSIONS[version]
    vs, ls = scheme.split()
    assert (
        format_version(
            version,
            version_scheme=vs,
            custom_version_scheme=None,
            local_scheme=ls,
            custom_local_scheme=None,
        )
        == expected
    )


CUSTOM_SCHEMES = {
    "full": {
        "clean_dev": "<clean_dev>",
        "dirty_dev": "<dirty_dev>",
        "clean_tag": "<clean_tag>",
        "dirty_tag": "<dirty_tag>",
    },
    "dirty": {"dirty_dev": "<dirty_dev>", "dirty_tag": "<dirty_tag>"},
    "clean": {"clean_dev": "<clean_dev>", "clean_tag": "<clean_tag>"},
}


@pytest.mark.parametrize(
    "version,scheme,expected",
    [
        ("exact", "full full", "<clean_tag><clean_tag>"),
        ("zerodistance", "full full", "<clean_tag><clean_tag>"),
        ("dirty", "full full", "<dirty_tag><dirty_tag>"),
        ("distance", "full full", "<clean_dev><clean_dev>"),
        ("distancedirty", "full full", "<dirty_dev><dirty_dev>"),
        ("exact", "dirty full", "1.1<clean_tag>"),
        ("zerodistance", "dirty full", "1.2.dev0<clean_tag>"),
        ("dirty", "dirty clean", "<dirty_tag>+d20090213"),
        ("distance", "dirty clean", "1.2.dev3<clean_dev>"),
        ("distancedirty", "full clean", "<dirty_dev>+d20090213"),
    ],
)
def test_custom_format_version(version, scheme, expected):
    version = VERSIONS[version]
    vs, ls = scheme.split()
    assert (
        format_version(
            version,
            version_scheme="guess-next-dev",
            custom_version_scheme=CUSTOM_SCHEMES[vs],
            local_scheme="node-and-date",
            custom_local_scheme=CUSTOM_SCHEMES[ls],
        )
        == expected
    )


def test_dump_version_doesnt_bail_on_value_error(tmpdir):
    write_to = "VERSION"
    version = str(VERSIONS["exact"].tag)
    with pytest.raises(ValueError) as exc_info:
        dump_version(tmpdir.strpath, version, write_to)
    assert str(exc_info.value).startswith("bad file format:")


@pytest.mark.parametrize(
    "version", ["1.0", "1.2.3.dev1+ge871260", "1.2.3.dev15+ge871260.d20180625"]
)
def test_dump_version_works_with_pretend(version, tmpdir, monkeypatch):
    monkeypatch.setenv(PRETEND_KEY, version)
    get_version(write_to=str(tmpdir.join("VERSION.txt")))
    assert tmpdir.join("VERSION.txt").read() == version


def test_has_command(recwarn):
    assert not has_command("yadayada_setuptools_aint_ne")
    msg = recwarn.pop()
    assert "yadayada" in str(msg.message)


@pytest.mark.parametrize(
    "tag, expected_version",
    [
        ("1.1", "1.1"),
        ("release-1.1", "1.1"),
        pytest.param("3.3.1-rc26", "3.3.1rc26", marks=pytest.mark.issue(266)),
    ],
)
def test_tag_to_version(tag, expected_version):
    version = str(tag_to_version(tag))
    assert version == expected_version
