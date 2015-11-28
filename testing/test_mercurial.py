from setuptools_scm import format_version
from setuptools_scm.hg import archival_to_version
from setuptools_scm import integration

import pytest


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


@pytest.mark.parametrize('expected,data', sorted(archival_mapping.items()))
def test_archival_to_version(expected, data):
    version = archival_to_version(data)
    assert format_version(
        version,
        version_scheme='guess-next-dev',
        local_scheme='node-and-date') == expected


def test_find_files_stop_at_root_hg(wd):
    wd('hg init')
    wd.write('test.txt', 'test')
    wd('hg add .')
    wd('hg commit -m test -u test')
    wd.cwd.ensure('project/setup.cfg')
    assert integration.find_files(str(wd.cwd/'project')) == []


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


def test_version_from_archival(wd):
    wd.write(
        '.hg_archival.txt',
        'node: 000000000000\n'
        'tag: 0.1\n'
    )
    assert wd.version == '0.1'

    wd.write(
        '.hg_archival.txt',
        'node: 000000000000\n'
        'latesttag: 0.1\n'
        'latesttagdistance: 3\n'
    )

    assert wd.version == '0.2.dev3+n000000000000'
