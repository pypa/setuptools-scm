from hgdistver import _data_from_archival, \
    _archival_to_version

import hgdistver
import py
code = py.code.Source(hgdistver)
setup_code = py.code.Source("""
    import hgdistver
    from setuptools import setup
    setup(
        name='test',
        version=hgdistver.get_version())
""")
from subprocess import call, Popen, PIPE


def write_base(path):
    path.join('hgdistver.py').write(code)

def spv(path, method='get_version', **kw):
    p = Popen(['python', '-c', 'import hgdistver;print hgdistver.%s(**%r)' % (method, kw)  ],
              cwd=str(path),
              stdout=PIPE,
              stderr=PIPE,
             )
    ver, _ = p.communicate()
    return ver.strip()


class sbrepo(object):
    def __init__(self, path):
        self.path = path
        self._hg('init')
        write_base(self.path)
        self.add('hgdistver.py')

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
        from functools import partial
        for method in metafunc.function.methods.args:
            metafunc.addcall(id=method, funcargs={'log_spv': partial(spv, method=method)})

@py.test.mark.methods('version_from_hg15_parents', 'version_from_hg_log_with_tags')
def test_version_from_hg_id(wd, log_spv):
    initial = log_spv(wd.path)
    assert initial.startswith('0.0.dev0-' + '0'*12 + '+') #uses node when no tag
    wd.commit(message='commit')

    after_first_commit = log_spv(wd.path)

    assert after_first_commit.startswith('0.0.dev1-')

    wd.tag('0.1')
    after_tag_01 = log_spv(wd.path)
    assert after_tag_01.startswith('0.1.dev1-')

    wd.up('0.1')
    at_tag_01 = spv(wd.path)
    assert at_tag_01 == '0.1'

def test_version_from_archival(tmpdir):
    write_base(tmpdir)
    tmpdir.join('.hg_archival.txt').write(
        'node: 000000000000\n'
        'tag: 0.1\n'
    )
    assert spv(tmpdir) == '0.1'


    tmpdir.join('.hg_archival.txt').write(
        'node: 000000000000\n'
        'latesttag: 0.1\n'
        'latesttagdistance: 3\n'
    )

    assert spv(tmpdir) == '0.1.dev3-000000000000'


def test_version_from_cachefile(tmpdir):
    write_base(tmpdir)

    tmpdir.join('test.txt').write(
        '# comment\n'
        'version = "1.0"'
    )

    assert spv(tmpdir, cachefile='test.txt') == '1.0'


def test_version_from_pkginfo(tmpdir):
    write_base(tmpdir)
    tmpdir.join('PKG-INFO').write('Version: 0.1')
    assert spv(tmpdir) == '0.1'
