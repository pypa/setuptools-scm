from functools import partial
import setuptools
import setuptools_scm

with open('README.rst') as fp:
    long_description = fp.read()


setup = partial(
    setuptools.setup,
    name='setuptools-scm',
    url='http://bitbucket.org/pypa/setptools_scm/',
    version=setuptools_scm.get_version(),
    author='Ronny Pfannschmidt',
    author_email='opensource@ronnypfannschmidt.de',
    description=('the blessed package to manage your versions by scm tags'),
    long_description=long_description,
    license='MIT',
    py_modules=[
        'setuptools_scm',
    ],
    entry_points={
        'distutils.setup_keywords': [
            'use_scm_version = setuptools_scm.setuptools_version_keyword'
        ],
        'setuptools.file_finders': [
            'setuptools_scm = setuptools_scm:find_files',
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
