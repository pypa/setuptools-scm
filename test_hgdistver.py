from hgdistver import _data_from_archival, \
    _archival_to_version
import os
import hgdistver
import py
from subprocess import call, Popen, PIPE
from functools import partial

def get_version(path, method='get_version', **kw):
    call = getattr(hgdistver, method)
    root = str(path)
    return call(root=root, **kw)

class sbrepo(object):
    def __init__(self, path):
        self.path = path
        self._hg('init')

    def add(self, *files):
        self._hg('add', *files)

    def commit(self, message):
        self._hg('commit',
                 '-m', message,
                 '-u', 'test',
                 '-d', '0 0',
                )
    def tag(self, tag):
        self._hg('tag', tag,
                 '-m', 'added tag %s' % tag,
                 '-u', 'test',
                 '-d', '0 0')

    def up(self, rev):
        self._hg('up', rev)

    def _hg(self, *args):
        return call(['hg'] + [str(arg) for arg in args],
                    cwd=str(self.path))

    def join(self, name):
        return self.path.join(name)

def pytest_funcarg__wd(request):
    tmpdir = request.getfuncargvalue('tmpdir')
    return sbrepo(tmpdir)

def test_data_from_archival(tmpdir):
    tmpfile = tmpdir.join('test.archival')
    tmpfile.write('name: test\nrevision: 1')

    res = _data_from_archival(tmpfile)
    assert res == {
        'name': 'test',
        'revision': '1',
    }


archival_mapping = {
    '1.0': {'tag': '1.0'},
    '1.0.dev3-000000000000': {
        'latesttag': '1.0',
        'latesttagdistance': '3',
        'node': '0'*20,
    },
    '0'*12: {
        'node': '0'*20,
    },

}

def test_archival_to_version():
    for expected, data in archival_mapping.items():
        assert _archival_to_version(data) == expected


def pytest_generate_tests(metafunc):
    if hasattr(metafunc.function, 'methods'):
        for method in metafunc.function.methods.args:
            metafunc.addcall(
                id=method,
                param=method,
            )

def pytest_funcarg__get_log_version(request):
    def get_log_version(path):
        return get_version(path, method=request.param)
    return get_log_version

@py.test.mark.methods('version_from_hg15_parents', 'version_from_hg_log_with_tags')
def test_version_from_hg_id(wd, get_log_version):
    initial = get_log_version(wd.path)
    assert initial.startswith('0.0.dev0-' + '0'*12 ) #uses node when no tag
    wd.path.join('test.txt').write('test')
    wd.add('test.txt')
    wd.commit(message='commit')

    after_first_commit = get_log_version(wd.path)

    assert after_first_commit.startswith('0.0.dev1-')

    wd.tag('0.1')
    after_tag_01 = get_log_version(wd.path)
    assert after_tag_01.startswith('0.1.dev1-')

    wd.up('0.1')
    at_tag_01 = get_version(wd.path)
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

    assert get_version(tmpdir) == '0.1.dev3-000000000000'


def test_version_from_cachefile(tmpdir):
    tmpdir.join('test.txt').write(
        '# comment\n'
        'version = "1.0"'
    )

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

def test_cachefiile_join(monkeypatch):
    def assert_join(root, cachefile):
        assert cachefile == '/tmp/cachefile'
    monkeypatch.setattr(hgdistver, 'methods', [assert_join])
    hgdistver.get_version(root='/tmp', cachefile='cachefile')



