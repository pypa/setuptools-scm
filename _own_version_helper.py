"""
this module is a hack only in place to allow for setuptools
to use the attribute for the versions
"""
from __future__ import annotations

from setuptools_scm import Configuration
from setuptools_scm import get_version
from setuptools_scm import git
from setuptools_scm import hg
from setuptools_scm.hacks import parse_pkginfo
from setuptools_scm.version import get_local_node_and_date
from setuptools_scm.version import guess_next_dev_version
from setuptools_scm.version import ScmVersion


def parse(root: str, config: Configuration) -> ScmVersion | None:
    try:
        return parse_pkginfo(root, config)
    except OSError:
        return git.parse(root, config=config) or hg.parse(root, config=config)


def scm_version() -> str:
    return get_version(
        relative_to=__file__,
        parse=parse,
        version_scheme=guess_next_dev_version,
        local_scheme=get_local_node_and_date,
    )
