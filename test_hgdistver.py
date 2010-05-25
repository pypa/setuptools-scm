from hgdistver import data_from_archival

def test_data_from_archival(tmpdir):
    tmpfile = tmpdir.join('test.archival')
    tmpfile.write('name: test\nrevision: 1')

    res = data_from_archival(tmpfile)
    assert res == {
        'name': 'test',
        'revision': '1',
    }

