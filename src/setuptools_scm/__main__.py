import sys

from setuptools_scm import _get_version
from setuptools_scm import get_version
from setuptools_scm.config import Configuration
from setuptools_scm.integration import find_files


def main() -> None:
    files = list(sorted(find_files("."), key=len))
    try:
        pyproject = next(fname for fname in files if fname.endswith("pyproject.toml"))
        print(_get_version(Configuration.from_file(pyproject)))
    except (LookupError, StopIteration):
        print("Guessed Version", get_version())

    if "ls" in sys.argv:
        for fname in files:
            print(fname)


if __name__ == "__main__":
    main()
