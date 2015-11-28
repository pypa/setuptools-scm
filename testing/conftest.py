import os
import pytest

os.environ['SETUPTOOLS_SCM_DEBUG'] = '1'
VERSION_PKGS = ['setuptools', 'setuptools_scm']


def pytest_report_header():
    import pkg_resources
    res = []
    for pkg in VERSION_PKGS:
        version = pkg_resources.get_distribution(pkg).version
        res.append('%s version %s' % (pkg, version))
    return res


class Wd(object):
    def __init__(self, cwd):
        self.cwd = cwd

    def __call__(self, cmd):
        from setuptools_scm.utils import do
        return do(cmd, self.cwd)

    def write(self, name, value):
        filename = self.cwd.join(name)
        filename.write(value)
        return filename

    @property
    def version(self):
        __tracebackhide__ = True
        from setuptools_scm import get_version
        version = get_version(root=str(self.cwd))
        print(version)
        return version


@pytest.fixture
def wd(tmpdir):
    return Wd(tmpdir)
