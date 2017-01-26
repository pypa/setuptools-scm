
from subprocess import call

import os

if os.environ['TOXENV']:
    import tox
    tox.cmdline()
elif os.environ['SELFINSTALL']:
    call('python setup.py sdist', shell=True)
    call('easy_install dist/*', shell=True)
    import pkg_ressources
    dist = pkg_ressources.get_distribution('setuptools_scm')
    assert dist.version != '0.0'
