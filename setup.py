"""\
important note:

the setup of setuptools_scm is self-using,
the first execution of `python setup.py egg_info`
will generate partial data
its critical to run `python setup.py egg_info`
once before running sdist or easy_install on a fresh checkouts

pip usage is recommended
"""
import os
import sys

import setuptools
from setuptools.command.bdist_egg import bdist_egg as original_bdist_egg


class bdist_egg(original_bdist_egg):
    def run(self):
        raise SystemExit(
            "%s is forbidden, "
            "please update to setuptools>=45 which uses pip" % type(self).__name__
        )


def scm_version():

    if sys.version_info < (3, 6):
        raise RuntimeError(
            "support for python < 3.6 has been removed in setuptools_scm>=6.0.0"
        )
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "src")

    sys.path.insert(0, src)

    from setuptools_scm import get_version
    from setuptools_scm.hacks import parse_pkginfo
    from setuptools_scm import git
    from setuptools_scm import hg
    from setuptools_scm.version import guess_next_dev_version, get_local_node_and_date

    def parse(root, config):
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
        cmdclass={"bdist_egg": bdist_egg},
    )
