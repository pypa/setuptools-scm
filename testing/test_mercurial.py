from setuptools_scm import format_version
from setuptools_scm.hg import archival_to_version

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
