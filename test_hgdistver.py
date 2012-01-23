import os
import py
import pytest

import hgdistver
from hgdistver import hg, \
    _data_from_archival, \
    _archival_to_version, \
    _hg_version



def pytest_generate_tests(metafunc):
    if hasattr(metafunc.function, 'cases'):
        metafunc.parametrize('case', metafunc.function.cases.args, indirect=True)

def pytest_funcarg__case(request):
    return request.param

def get_version(path, method='get_version', **kw):
    call = getattr(hgdistver, method)
    root = str(path)
    return call(root=root, **kw)



def test_data_from_archival(tmpdir):
    tmpfile = tmpdir.join('test.archival')
    tmpfile.write('name: test\nrevision: 1')

    res = _data_from_archival(str(tmpfile))
    assert res == {
        'name': 'test',
        'revision': '1',
    }


archival_mapping = {
    '1.0': {'tag': '1.0'},
    '1.0.post3-000000000000': {
        'latesttag': '1.0',
        'latesttagdistance': '3',
        'node': '0'*20,
    },
    '0'*12: {
        'node': '0'*20,
    },
    '1.2.2': {'tag': 'release-1.2.2'},
    '1.2.2a1': {'tag': 'release-1.2.2a1'},

}

def pytest_funcarg__data(request): return request.param
def pytest_funcarg__expected(request): return request.param

@pytest.mark.parametrize('expected data'.split(), archival_mapping.items(), archival_mapping)
def test_archival_to_version(expected, data):
    assert _archival_to_version(data) == expected



def pytest_funcarg__get_log_version(request):
    case = request.getfuncargvalue('case')

    def get_log_version(path):
        return get_version(path, method=case)
    get_log_version.__name__ = case
    return get_log_version

#XXX: better tests for tag prefixes
@py.test.mark.cases('version_from_hg15_parents', 'version_from_hg_log_with_tags')
def test_version_from_hg_id(tmpdir, get_log_version):
    hgv = _hg_version()
    print(hgv)
    if hgv < '1.5' and 'parents' in get_log_version.kind:
        py.test.skip('hg too old, this test needs >=1.5')
    cwd = str(tmpdir)
    hg('init', cwd)
    initial = get_log_version(cwd)
    assert initial.startswith('0.0.post0-' + '0'*12 ) #uses node when no tag
    tmpdir.join('test.txt').write('test')
    hg('add test.txt', cwd)
    hg('commit -m commit -u test -d "0 0"', cwd)

    after_first_commit = get_log_version(cwd)

    assert after_first_commit.startswith('0.0.post1-')

    hg('tag v0.1 -u test -d "0 0"', cwd)
    after_tag_01 = get_log_version(cwd)
    assert after_tag_01.startswith('0.1.post1-')

    hg('up v0.1', cwd)
    at_tag_01 = get_version(cwd)
    assert at_tag_01 == '0.1'

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

    assert get_version(tmpdir) == '0.1.post3-000000000000'


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


