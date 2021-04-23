import sys
from setuptools_scm import get_version
from setuptools_scm.integration import find_files


def main():
    if "increment" in sys.argv:
        print(get_version(version_scheme="increment", local_scheme="no-local-version"))
    else:
        print("Guessed Version", get_version())
        if "ls" in sys.argv:
            for fname in find_files("."):
                print(fname)


if __name__ == "__main__":
    main()
