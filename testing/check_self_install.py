import pkg_resources

import setuptools_scm

dist = pkg_resources.get_distribution("setuptools_scm")
assert dist.version == setuptools_scm.get_version(), dist.version
