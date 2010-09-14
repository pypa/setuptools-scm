from setuptools import setup
import hgdistver
setup(
    name='hgdistver',
    url='http://bitbucket.org/RonnyPfannschmidt/hgdistver/',
    version=hgdistver.get_version(),
    author='Ronny Pfannschmidt',
    author_email='Ronny Pfannschmidt <Ronny.Pfannschmidt@gmx.de>',
    description='utility lib to generate python package version infos from mercurial tags',
    long_description=open('README.txt').read(),
    license='MIT',
    py_modules=[
        'hgdistver',
    ],
    entry_points={
        'distutils.setup_keywords': [
            'get_version_from_hg = hgdistver:setuptools_version_keyword',
            'cache_hg_version_to = hgdistver:setuptools_cachefile_keyword',
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


