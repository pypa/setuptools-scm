from __future__ import print_function
import sys
from setuptools_scm import get_version, find_files

if __name__ == '__main__':
    print('Guessed Version', get_version())
    if 'ls' in sys.argv:
        for fname in find_files('.'):
            print(fname)
