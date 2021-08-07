"""
integration tests that check setuptools version support
"""
import os
import subprocess
import sys

import pytest


@pytest.fixture(scope="session")
def get_setuptools_packagedir(request):
    targets = request.config.cache.makedir("setuptools_installs")

    def makeinstall(version):
        target = targets.ensure(version, dir=1)
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-binary",
                "setuptools",
                "setuptools==" + version,
                "-t",
                str(target),
            ]
        )
        return target

    return makeinstall


SCRIPT = """
from __future__ import print_function
import sys
import setuptools
print(setuptools.__version__, 'expected', sys.argv[1])
import setuptools_scm.version
from setuptools_scm.__main__ import main
main()
"""


def check(packagedir, expected_version, **env):

    old_pythonpath = os.environ.get("PYTHONPATH")
    if old_pythonpath:
        pythonpath = f"{old_pythonpath}:{packagedir}"
    else:
        pythonpath = str(packagedir)
    subprocess.check_call(
        [sys.executable, "-c", SCRIPT, expected_version],
        env=dict(os.environ, PYTHONPATH=pythonpath, **env),
    )


def test_distlib_setuptools_works(get_setuptools_packagedir):
    packagedir = get_setuptools_packagedir("45.0.0")
    check(packagedir, "45.0.0")
