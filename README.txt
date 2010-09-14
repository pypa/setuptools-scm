hgdistver
~~~~~~~~~

This module is a simple drop-in to support setup.py
in mercurial based projects.

Alternatively it can be a setup time requirement.

Its supposed to generate version numbers from mercurials meta-data.
It tries to use the current tag and
falls back to the next reachable tagged ancestor and
using the distance to it as .post marker.

It uses 4 strategies to archive its task:

1. try to directly ask hg for the tag/distance
2. try to infer it from the `.hg_archival.txt` file
3. try to use the cache file if it exists
4. try to read the version from the 'PKG-INFO' file sdists contain (this is a nasty abuse)

The most simple usage is::

    from setuptools import setup
    from hgdistver import get_version
    setup(
        ...,
        version=get_version(),
        ...,
    )

`get_version` takes the optional argument `cachefile`,
which causes it to store the version info in a python script instead
of abusing PKG-INFO from a sdist.


The setup requirement usage is::

    from setuptools import setup
    setup(
        ...,
        get_version_from_hg=True,
        setup_requires=['hgdistver'],
        ...,
    )

The requirement uses the setup argument cache_hg_version_to instead of cachefile.
