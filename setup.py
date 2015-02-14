from functools import partial
import setuptools
with open('README.rst') as fp:
    long_description = fp.read()


setup = partial(
    setuptools.setup,
    name='hgdistver',
    url='http://bitbucket.org/RonnyPfannschmidt/hgdistver/',
    get_version_from_scm=True,
    author='Ronny Pfannschmidt',
    author_email='opensource@ronnypfannschmidt.de',
    description=('utility to generate python package '
                 'version infos from mercurial/git tags'),
    long_description=long_description,
    license='MIT',
    py_modules=[
        'hgdistver',
    ],
    setup_requires=[
        'hgdistver[files]',
    ],
    extras_require={'files': []},
    entry_points={
        'distutils.setup_keywords': [
            'get_version_from_hg = hgdistver:setuptools_version_keyword',
            'get_version_from_scm = hgdistver:setuptools_version_keyword',
            'cache_hg_version_to = hgdistver:setuptools_cachefile_keyword',
            'guess_next_version = hgdistver:setuptools_cachefile_keyword',
        ],
        'setuptools.file_finders': [
            'hgdistver = hgdistver:find_files [files]',
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
