"""
:copyright: 2010-2015 by Ronny Pfannschmidt
:license: MIT
"""
import os

from .utils import trace
from .version import format_version
from .discover import find_matching_entrypoint


def version_from_scm(root):
    ep = find_matching_entrypoint(root, 'setuptools_scm.parse_scm')
    if ep:
        return ep.load()(root)


def get_version(root='.',
                version_scheme='guess-next-dev',
                local_scheme='node-and-date',
                ):
    root = os.path.abspath(root)
    trace('root', repr(root))

    version = version_from_scm(root)

    if version:
        if isinstance(version, str):
            return version
        return format_version(
            version,
            version_scheme=version_scheme,
            local_scheme=local_scheme)
        return version
