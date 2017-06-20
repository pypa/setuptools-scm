import pytest
import py
import sys
import pkg_resources
from setuptools_scm import dump_version, get_version, PRETEND_KEY
from setuptools_scm.version import guess_next_version, meta, format_version
from setuptools_scm.utils import has_command
import subprocess

PY3 = sys.version_info > (2,)


class MockTime(object):
    def __format__(self, *k):
        return 'time'


@pytest.mark.parametrize('tag, expected', [
    ('1.1', '1.2.dev0'),
    ('1.2.dev', '1.2.dev0'),
    ('1.1a2', '1.1a3.dev0'),
    ('23.24.post2+deadbeef', '23.24.post3.dev0'),
    ])
def test_next_tag(tag, expected):
    version = pkg_resources.parse_version(tag)
    assert guess_next_version(version, 0) == expected


VERSIONS = {
    'exact': meta('1.1', None, False),
    'zerodistance': meta('1.1', 0, False),
    'dirty': meta('1.1', None, True),
    'distance': meta('1.1', 3, False),
    'distancedirty': meta('1.1', 3, True),
}


@pytest.mark.parametrize('version,scheme,expected', [
    ('exact', 'guess-next-dev node-and-date', '1.1'),
    ('zerodistance', 'guess-next-dev node-and-date', '1.2.dev0'),
    ('dirty', 'guess-next-dev node-and-date', '1.2.dev0+dtime'),
    ('distance', 'guess-next-dev node-and-date', '1.2.dev3'),
    ('distancedirty', 'guess-next-dev node-and-date', '1.2.dev3+dtime'),
    ('exact', 'post-release node-and-date', '1.1'),
    ('zerodistance', 'post-release node-and-date', '1.1.post0'),
    ('dirty', 'post-release node-and-date', '1.1.post0+dtime'),
    ('distance', 'post-release node-and-date', '1.1.post3'),
    ('distancedirty', 'post-release node-and-date', '1.1.post3+dtime'),
])
def test_format_version(version, monkeypatch, scheme, expected):
    version = VERSIONS[version]
    monkeypatch.setattr(version, 'time', MockTime())
    vs, ls = scheme.split()
    assert format_version(
        version,
        version_scheme=vs,
        local_scheme=ls) == expected


def test_dump_version_doesnt_bail_on_value_error(tmpdir):
    write_to = "VERSION"
    version = str(VERSIONS['exact'].tag)
    with pytest.raises(ValueError) as exc_info:
        dump_version(tmpdir.strpath, version, write_to)
    assert str(exc_info.value).startswith("bad file format:")


def test_dump_version_works_with_pretend(tmpdir, monkeypatch):
    monkeypatch.setenv(PRETEND_KEY, '1.0')
    get_version(write_to=str(tmpdir.join('VERSION.txt')))
    assert tmpdir.join('VERSION.txt').read() == '1.0'


def test_has_command(recwarn):
    assert not has_command('yadayada_setuptools_aint_ne')
    msg = recwarn.pop()
    assert 'yadayada' in str(msg.message)


def _get_windows_short_path(path):
    """ Call a temporary batch file that expands the first argument so that
    it contains short names only.
    Return a py._path.local.LocalPath instance.

    For info on Windows batch parameters:
    https://www.microsoft.com/resources/documentation/windows/xp/all/proddocs/en-us/percent.mspx?mfr=true
    """
    tmpdir = py.path.local.mkdtemp()
    try:
        batch_file = tmpdir.join("shortpathname.bat")
        batch_file.write("@echo %~s1")
        out = subprocess.check_output([str(batch_file), str(path)])
        if PY3:
            out = out.decode(sys.getfilesystemencoding())
    finally:
        tmpdir.remove()
    return py.path.local(out.strip())


@pytest.mark.skipif(sys.platform != 'win32',
                    reason="this test is only valid on windows")
def test_get_windows_long_path_name(tmpdir):
    from setuptools_scm.utils import get_windows_long_path_name

    # 8.3 names are limited to max 8 characters, plus optionally a period
    # and three further characters; so here we use longer names
    file_a = tmpdir.ensure("long_name_a.txt")
    file_b = tmpdir.ensure("long_name_b.txt")
    dir_c = tmpdir.ensure("long_name_c", dir=True)
    short_file_a = _get_windows_short_path(file_a)
    short_file_b = _get_windows_short_path(file_b)
    short_dir_c = _get_windows_short_path(dir_c)

    # shortened names contain the first six characters (case insensitive),
    # followed by a tilde character and an incremental number that
    # distinguishes files with the same first six letters and extension
    assert short_file_a.basename == "LONG_N~1.TXT"
    assert short_file_b.basename == "LONG_N~2.TXT"
    assert short_dir_c.basename == "LONG_N~1"

    long_name_a = get_windows_long_path_name(str(short_file_a))
    long_name_b = get_windows_long_path_name(str(short_file_b))
    long_name_c = get_windows_long_path_name(str(short_dir_c))
    assert long_name_a.endswith("long_name_a.txt")
    assert long_name_b.endswith("long_name_b.txt")
    assert long_name_c.endswith("long_name_c")

    # check ctypes.WinError() with no arg shows the last error message, e.g.
    # when input path doesn't exist. Note, WinError is not itself a subclass
    # of BaseException; it's a function returning an instance of OSError
    with pytest.raises(OSError) as excinfo:
        get_windows_long_path_name("unexistent_file_name")
    assert 'The system cannot find the file specified' in str(excinfo)
