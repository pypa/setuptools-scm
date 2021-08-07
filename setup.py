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


def scm_config():

    if sys.version_info < (3, 6):
        raise RuntimeError(
            "support for python < 3.6 has been removed in setuptools_scm>=6.0.0"
        )

    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "src")
    egg_info = os.path.join(src, "setuptools_scm.egg-info")
    has_entrypoints = os.path.isdir(egg_info)
    import pkg_resources

    pkg_resources.require("setuptools>=45")

    sys.path.insert(0, src)
    pkg_resources.working_set.add_entry(src)
    # FIXME: remove debug
    print(src)
    print(pkg_resources.working_set)

    from setuptools_scm.hacks import parse_pkginfo
    from setuptools_scm.git import parse as parse_git
    from setuptools_scm.version import guess_next_dev_version, get_local_node_and_date

    def parse(root):
        try:
            return parse_pkginfo(root)
        except OSError:
            return parse_git(root)

    config = dict(
        version_scheme=guess_next_dev_version, local_scheme=get_local_node_and_date
    )

    if has_entrypoints:
        return dict(use_scm_version=config)
    else:
        from setuptools_scm import get_version

        return dict(version=get_version(root=here, parse=parse, **config))


if __name__ == "__main__":
    setuptools.setup(**scm_config())
