"""\
important note:

the setup of setuptools_scm is self-using,
the first execution of `python setup.py egg_info`
will generate partial data
its critical to run `python setup.py egg_info`
once before running sdist or easy_install on a fresh checkouts

pip usage is recommended
"""
from __future__ import annotations

import os
import sys

import setuptools


def scm_version() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "src")

    sys.path.insert(0, src)

    from setuptools_scm import get_version
    from setuptools_scm.hacks import parse_pkginfo
    from setuptools_scm import git
    from setuptools_scm import hg
    from setuptools_scm.version import guess_next_dev_version, get_local_node_and_date
    from setuptools_scm.config import Configuration

    from setuptools_scm.version import ScmVersion

    def parse(root: str, config: Configuration) -> ScmVersion | None:
        try:
            return parse_pkginfo(root, config)
        except OSError:
            return git.parse(root, config=config) or hg.parse(root, config=config)

    return get_version(
        root=here,
        parse=parse,
        version_scheme=guess_next_dev_version,
        local_scheme=get_local_node_and_date,
    )


if __name__ == "__main__":
    setuptools.setup(
        version=scm_version(),
        extras_require={
            "toml": [
                "setuptools>=42",
            ],
            "test": ["pytest>=6.2", "virtualenv>20"],
        },
    )
