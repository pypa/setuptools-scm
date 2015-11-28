from setuptools_scm import integration


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


def test_find_files_stop_at_root_git(wd):
    wd('git init')
    wd.write('test.txt', 'test')
    wd('git add .')
    wd('git commit -m test -u test')
    wd.cwd.ensure('project/setup.cfg')
    assert integration.find_files(str(wd.cwd/'project')) == []
