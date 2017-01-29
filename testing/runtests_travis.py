
from subprocess import call

import os

if os.environ.get('TOXENV'):
    import tox
    tox.cmdline()
elif os.environ.get('SELFINSTALL'):
    call('python setup.py sdist', shell=True)
    call('easy_install dist/*', shell=True)
    import pkg_resources
    dist = pkg_resources.get_distribution('setuptools_scm')
    assert dist.version != '0.0'
