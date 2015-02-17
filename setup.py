"""
important note:

this package is self-using,
the first execution of setup.py egg_info
will generate partial data
its critical to run egg_info
once before running sdist in a fresh checkouts
"""

from functools import partial
import setuptools

with open('README.rst') as fp:
    long_description = fp.read()


setup = partial(
    setuptools.setup,
    name='setuptools-scm',
    url='http://bitbucket.org/pypa/setptools_scm/',
    use_scm_version=True,
    author='Ronny Pfannschmidt',
    author_email='opensource@ronnypfannschmidt.de',
    description=('the blessed package to manage your versions by scm tags'),
    long_description=long_description,
    license='MIT',
    packages=[
        'setuptools_scm',
    ],
    entry_points={
        'distutils.setup_keywords': [
            'use_scm_version = setuptools_scm:setuptools_version_keyword'
        ],
        'setuptools.file_finders': [
            'setuptools_scm = setuptools_scm:find_files',
        ],
        'setuptools_scm.parse_scm': [
            '.hg = setuptools_scm.hg:parse',
            '.git = setuptools_scm.git:parse',
            '.hg_archival.txt = setuptools_scm.hg:parse_archival',
            'PKG-INFO = setuptools_scm.hacks:parse_pkginfo',
        ],
        'setuptools_scm.files_command': [
            '.hg = setuptools_scm.hg:FILES_COMMAND',
            '.git = setuptools_scm.git:FILES_COMMAND',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Version Control',
        'Topic :: System :: Software Distribution',
        'Topic :: Utilities',
    ],
)
if __name__ == '__main__':
    setup()
