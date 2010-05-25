from hgdistver import _data_from_archival, \
    _archival_to_version


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
