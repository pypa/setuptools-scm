# ~/~ begin <<docs/customizing.md#docs/examples/version_scheme_code/setup.py>>[init]
# we presume installed build dependencies
from __future__ import annotations

from setuptools import setup

from setuptools_scm import ScmVersion


def myversion_func(version: ScmVersion) -> str:
    from setuptools_scm.version import guess_next_version

    return version.format_next_version(guess_next_version, "{guessed}b{distance}")


setup(use_scm_version={"version_scheme": myversion_func})
# ~/~ end
