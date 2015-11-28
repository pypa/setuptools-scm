import os
import py
import pytest

import setuptools_scm
from setuptools_scm import format_version
from setuptools_scm import integration
from setuptools_scm import dump_version


from setuptools_scm.utils import data_from_mime, do


def get_version(root, method='get_version', __tracebackhide__=False, **kw):
    call = getattr(setuptools_scm, method)
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
        return do(cmd, self.cwd)

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

    res = data_from_mime(str(tmpfile))
    assert res == {
        'name': 'test',
        'revision': '1',
    }



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
    assert get_version(tmpdir) == '0.1'

    tmpdir.join('.hg_archival.txt').write(
        'node: 000000000000\n'
        'latesttag: 0.1\n'
        'latesttagdistance: 3\n'
    )

    assert get_version(tmpdir) == '0.2.dev3+n000000000000'


def test_version_from_pkginfo(tmpdir):
    tmpdir.join('PKG-INFO').write('Version: 0.1')
    assert get_version(tmpdir) == '0.1'


def assert_root(monkeypatch, expected_root):
    """
    Patch version_from_scm to simply assert that root is expected root
    """
    def assertion(root):
        assert root == expected_root
    monkeypatch.setattr(setuptools_scm, 'version_from_scm', assertion)


def test_root_parameter_creation(monkeypatch):
    assert_root(monkeypatch, os.getcwd())
    setuptools_scm.get_version()


def test_root_parameter_pass_by(monkeypatch):
    assert_root(monkeypatch, '/tmp')
    setuptools_scm.get_version(root='/tmp')


def test_root_relative_to(monkeypatch):
    assert_root(monkeypatch, '/tmp/alt')
    __file__ = '/tmp/module/file.py'
    setuptools_scm.get_version(root='../alt', relative_to=__file__)


def test_find_files_stop_at_root_hg(wd):
    wd('hg init')
    wd.write('test.txt', 'test')
    wd('hg add .')
    wd('hg commit -m test -u test')
    wd.cwd.ensure('project/setup.cfg')
    assert integration  .find_files(str(wd.cwd/'project')) == []


def test_find_files_stop_at_root_git(wd):
    wd('git init')
    wd.write('test.txt', 'test')
    wd('git add .')
    wd('git commit -m test -u test')
    wd.cwd.ensure('project/setup.cfg')
    assert integration.find_files(str(wd.cwd/'project')) == []


def test_dump_version(tmpdir):
    sp = tmpdir.strpath

    dump_version(sp, '1.0', 'first.txt')
    assert tmpdir.join('first.txt').read() == '1.0'
    dump_version(sp, '1.0', 'first.py')
    content = tmpdir.join('first.py').read()
    assert repr('1.0') in content
    import ast
    ast.parse(content)
