import os
import py
import pytest

import hgdistver
from hgdistver import (
    do,
    _data_from_mime,
    _archival_to_version,
    format_version,
)


def get_version(root, method='get_version', __tracebackhide__=False, **kw):
    call = getattr(hgdistver, method)
    data = call(root=root.strpath, **kw)
    if isinstance(data, dict):
        return format_version(data)
    else:
        return data


@pytest.mark.parametrize('cmd', ['ls', 'dir'])
def test_do(cmd, tmpdir):
    if not py.path.local.sysfind(cmd):
        pytest.skip(cmd + ' not found')
    do(cmd, str(tmpdir))


class Wd(object):
    def __init__(self, cwd):
        self.cwd = cwd

    def __call__(self, cmd):
        do(cmd, str(self.cwd))

    def write(self, name, value):
        filename = self.cwd.join(name)
        filename.write(value)
        return filename

    @property
    def version(self):
        __tracebackhide__ = True
        version = get_version(self.cwd, __tracebackhide__=True)
        print(version)
        return version


@pytest.fixture
def wd(tmpdir):
    return Wd(tmpdir)


def test_data_from_mime(wd):
    tmpfile = wd.write(
        'test.archival',
        'name: test\nrevision: 1')

    res = _data_from_mime(str(tmpfile))
    assert res == {
        'name': 'test',
        'revision': '1',
    }


archival_mapping = {
    '1.0': {'tag': '1.0'},
    '1.1.dev3+n000000000000': {
        'latesttag': '1.0',
        'latesttagdistance': '3',
        'node': '0'*20,
    },
    '0.0': {
        'node': '0'*20,
    },
    '1.2.2': {'tag': 'release-1.2.2'},
    '1.2.2.dev0': {'tag': 'release-1.2.2.dev'},

}


@pytest.fixture(params=sorted(archival_mapping))
def expected(request):
    return request.param


@pytest.fixture
def data(expected):
    return archival_mapping[expected]


def test_archival_to_version(expected, data):

    assert format_version(_archival_to_version(data)) == expected


def test_version_from_git(wd):
    wd('git init')
    wd('git config user.email test@example.com')
    wd('git config user.name "a test"')
    assert wd.version == '0.0'
    wd.write('test.txt', 'test')
    wd('git add test.txt')
    wd('git commit -m commit')

    assert wd.version.startswith('0.1.dev1+')
    assert not wd.version.endswith('1-')

    wd('git tag v0.1')
    assert wd.version == '0.1'

    wd.write('test.txt', 'test2')
    assert wd.version.startswith('0.2.dev0+')
    wd('git add test.txt')
    wd('git commit -m commit')
    assert wd.version.startswith('0.2.dev1+')
    wd('git tag version-0.2')
    assert wd.version.startswith('0.2')


# XXX: better tests for tag prefixes
def test_version_from_hg_id(wd):
    wd('hg init')
    assert wd.version == '0.0'
    wd.write('test.txt', 'test')
    wd('hg add test.txt')
    wd('hg commit -m commit -u test -d "0 0"')

    assert wd.version.startswith('0.1.dev2+')

    # tagging commit is considered the tag
    wd('hg tag v0.1 -u test -d "0 0"')
    assert wd.version == '0.1'
    wd.write('test.txt', 'test2')

    wd('hg commit -m commit2 -u test -d "0 0"')

    assert wd.version.startswith('0.2.dev2')

    wd('hg up v0.1')
    assert wd.version == '0.1'

    # commit originating from the taged revision
    # that is not a actual tag
    wd.write('test.txt', 'test2')
    wd('hg commit -m commit3 -u test -d "0 0"')
    assert wd.version.startswith('0.2.dev1+')


def test_version_from_archival(tmpdir):
    tmpdir.join('.hg_archival.txt').write(
        'node: 000000000000\n'
        'tag: 0.1\n'
    )
    subdir = tmpdir.join('test').ensure(dir=True)
    assert get_version(tmpdir) == '0.1'
    assert get_version(subdir) == '0.1'

    tmpdir.join('.hg_archival.txt').write(
        'node: 000000000000\n'
        'latesttag: 0.1\n'
        'latesttagdistance: 3\n'
    )

    assert get_version(tmpdir) == '0.2.dev3+n000000000000'


def test_version_from_cachefile(tmpdir):
    hgdistver.write_cachefile(str(tmpdir/'test.txt'), '1.0')
    assert get_version(tmpdir, cachefile='test.txt') == '1.0'


def test_version_from_pkginfo(tmpdir):
    tmpdir.join('PKG-INFO').write('Version: 0.1')
    assert get_version(tmpdir, method='version_from_sdist_pkginfo') == '0.1'


def test_root_parameter_creation(monkeypatch):
    def assert_cwd(root, cachefile=None):
        assert root == os.getcwd()
    monkeypatch.setattr(hgdistver, 'methods', [assert_cwd])
    hgdistver.get_version()


def test_root_parameter_pass_by(monkeypatch):
    def assert_root_tmp(root, cachefile):
        assert root == '/tmp'
    monkeypatch.setattr(hgdistver, 'methods', [assert_root_tmp])
    hgdistver.get_version(root='/tmp')


def test_cachefile_join(monkeypatch):
    def assert_join(root, cachefile):
        assert cachefile == os.path.join('tmp', 'cachefile')
    monkeypatch.setattr(hgdistver, 'methods', [assert_join])
    hgdistver.get_version(root='tmp', cachefile='cachefile')


def test_recreate_cachefile_from_pkginfo(tmpdir):
    tmpdir.join('PKG-INFO').write('Version: 0.1')
    assert not tmpdir.join('cachefile.txt').check()
    ver = get_version(tmpdir, cachefile='cachefile.txt')
    assert ver == '0.1'
    assert tmpdir.join('cachefile.txt').check()
