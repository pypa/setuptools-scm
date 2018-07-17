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
from setuptools_scm.utils import has_command

PY3 = sys.version_info > (2,)


class MockTime(object):

    def __format__(self, *k):
        return "time"


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


VERSIONS = {
    "exact": meta("1.1", distance=None, dirty=False),
    "zerodistance": meta("1.1", distance=0, dirty=False),
    "dirty": meta("1.1", distance=None, dirty=True),
    "distance": meta("1.1", distance=3, dirty=False),
    "distancedirty": meta("1.1", distance=3, dirty=True),
}


@pytest.mark.parametrize(
    "version,scheme,expected",
    [
        ("exact", "guess-next-dev node-and-date", "1.1"),
        ("zerodistance", "guess-next-dev node-and-date", "1.2.dev0"),
        ("dirty", "guess-next-dev node-and-date", "1.2.dev0+dtime"),
        ("distance", "guess-next-dev node-and-date", "1.2.dev3"),
        ("distancedirty", "guess-next-dev node-and-date", "1.2.dev3+dtime"),
        ("exact", "post-release node-and-date", "1.1"),
        ("zerodistance", "post-release node-and-date", "1.1.post0"),
        ("dirty", "post-release node-and-date", "1.1.post0+dtime"),
        ("distance", "post-release node-and-date", "1.1.post3"),
        ("distancedirty", "post-release node-and-date", "1.1.post3+dtime"),
    ],
)
def test_format_version(version, monkeypatch, scheme, expected):
    version = VERSIONS[version]
    monkeypatch.setattr(version, "time", MockTime())
    vs, ls = scheme.split()
    assert format_version(version, version_scheme=vs, local_scheme=ls) == expected


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
