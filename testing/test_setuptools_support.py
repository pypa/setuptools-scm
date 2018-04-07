"""
integration tests that check setuptools version support
"""
import sys
import os
import subprocess
import pytest
pytestmark = pytest.mark.skipif(
    "sys.version_info >= (3,6,0)",
    reason="integration with old versions no longer needed on py3.6+")


@pytest.fixture(scope='session')
def get_setuptools_packagedir(request):
    targets = request.config.cache.makedir('setuptools_installs')

    def makeinstall(version):
        target = targets.ensure(version, dir=1)
        subprocess.check_call([
            sys.executable, '-m', 'pip',
            'install', '--no-binary', 'setuptools', 'setuptools==' + version,
            '-t', str(target),
        ])
        return target
    return makeinstall


SCRIPT = """
import setuptools
print(setuptools.__version__)
import setuptools_scm.version
from setuptools_scm.__main__ import main
main()
"""


def check(packagedir, **env):
    subprocess.check_call(
        [sys.executable, '-c', SCRIPT],
        env=dict(os.environ, PYTHONPATH=".:" + str(packagedir), **env))


def test_old_setuptools_fails(get_setuptools_packagedir):
    packagedir = get_setuptools_packagedir("0.9.8")
    with pytest.raises(subprocess.CalledProcessError):
        check(packagedir)


def test_old_setuptools_allows_with_warnings(get_setuptools_packagedir):

    packagedir = get_setuptools_packagedir("0.9.8")
    # filter using warning since in the early python startup
    check(
        packagedir,
        PYTHONWARNINGS="once::Warning")


def test_distlib_setuptools_works(get_setuptools_packagedir):
    packagedir = get_setuptools_packagedir("12.0.1")
    check(packagedir)
