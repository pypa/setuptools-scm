import argparse
import os
import sys

from setuptools_scm import _get_version
from setuptools_scm.config import Configuration
from setuptools_scm.discover import walk_potential_roots
from setuptools_scm.integration import find_files


def main() -> None:
    opts = _get_cli_opts()
    root = opts.root or "."

    try:
        pyproject = opts.config or _find_pyproject(root)
        root = opts.root or os.path.relpath(os.path.dirname(pyproject))
        config = Configuration.from_file(pyproject, root=root)
    except (LookupError, FileNotFoundError) as ex:
        # no pyproject.toml OR no [tool.setuptools_scm]
        print(
            f"Warning: could not use {os.path.relpath(pyproject)},"
            " using default configuration.\n"
            f" Reason: {ex}.",
            file=sys.stderr,
        )
        config = Configuration(root=root)

    version = _get_version(config)
    assert version is not None
    if opts.strip_dev:
        version = version.partition(".dev")[0]
    print(version)

    if opts.command == "ls":
        for fname in find_files(config.root):
            print(fname)


def _get_cli_opts() -> argparse.Namespace:
    prog = "python -m setuptools_scm"
    desc = "Print project version according to SCM metadata"
    parser = argparse.ArgumentParser(prog, description=desc)
    # By default, help for `--help` starts with lower case, so we keep the pattern:
    parser.add_argument(
        "-r",
        "--root",
        default=None,
        help='directory managed by the SCM, default: inferred from config file, or "."',
    )
    parser.add_argument(
        "-c",
        "--config",
        default=None,
        metavar="PATH",
        help="path to 'pyproject.toml' with setuptools_scm config, "
        "default: looked up in the current or parent directories",
    )
    parser.add_argument(
        "--strip-dev",
        action="store_true",
        help="remove the dev/local parts of the version before printing the version",
    )
    sub = parser.add_subparsers(title="extra commands", dest="command", metavar="")
    # We avoid `metavar` to prevent printing repetitive information
    desc = "List files managed by the SCM"
    sub.add_parser("ls", help=desc[0].lower() + desc[1:], description=desc)
    return parser.parse_args()


def _find_pyproject(parent: str) -> str:
    for directory in walk_potential_roots(os.path.abspath(parent)):
        pyproject = os.path.join(directory, "pyproject.toml")
        if os.path.isfile(pyproject):
            return pyproject

    return os.path.abspath(
        "pyproject.toml"
    )  # use default name to trigger the default errors


if __name__ == "__main__":
    main()
