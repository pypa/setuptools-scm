hgdistver
~~~~~~~~~

This module is a simple drop-in to support setup.py
in mercurial based projects.

Its supposed to generate version numbers from mercurials metadata.

it uses 4 stategies to archive its taks:

1. try to directly ask hg for the metadata
2. try to infer it from the `.hg_archival.txt` file
3. try to use the cachefile if it exists
4. try to read the version from the 'PKG-INFO' file sdists contain

the most simple usage is::

    from setuptools import setup
    from hgdistver import get_version
    setup(
        ...,
        version=get_version(),
        ...,
    )

get_version takes the optional argument cachefile,
which causes it to store the version info in a python script instead
of abusing PKG-INFO from a sdist
