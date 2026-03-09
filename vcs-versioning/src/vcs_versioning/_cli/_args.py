from __future__ import annotations

import argparse


class CliNamespace(argparse.Namespace):
    """Typed namespace for CLI arguments."""

    # Main arguments
    root: str | None
    config: str | None
    strip_dev: bool
    no_version: bool
    format: str
    query: list[str] | None
    force_write_version_files: bool
    command: str | None

    # create-archival-file subcommand arguments
    archival_template: str | None
    force: bool


def get_cli_parser(prog: str) -> argparse.ArgumentParser:
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
        help="path to 'pyproject.toml' with setuptools-scm config, "
        "default: looked up in the current or parent directories",
    )
    parser.add_argument(
        "--strip-dev",
        action="store_true",
        help="remove the dev/local parts of the version before printing the version",
    )
    parser.add_argument(
        "-N",
        "--no-version",
        action="store_true",
        help="do not include package version in the output",
    )
    output_formats = ["json", "plain", "key-value"]
    parser.add_argument(
        "-f",
        "--format",
        type=str.casefold,
        default="plain",
        help="specify output format",
        choices=output_formats,
    )
    parser.add_argument(
        "-q",
        "--query",
        type=str.casefold,
        nargs="*",
        help="display setuptools-scm settings according to query, "
        "e.g. dist_name, do not supply an argument in order to "
        "print a list of valid queries.",
    )
    parser.add_argument(
        "--force-write-version-files",
        action="store_true",
        help="trigger to write the content of the version files\n"
        "its recommended to use normal/editable installation instead)",
    )
    sub = parser.add_subparsers(title="extra commands", dest="command", metavar="")
    # We avoid `metavar` to prevent printing repetitive information
    desc = "List information about the package, e.g. included files"
    sub.add_parser("ls", help=desc[0].lower() + desc[1:], description=desc)

    # Add create-archival-file subcommand
    archival_desc = "Create .git_archival.txt file for git archive support"
    archival_parser = sub.add_parser(
        "create-archival-file",
        help=archival_desc[0].lower() + archival_desc[1:],
        description=archival_desc,
    )
    archival_group = archival_parser.add_mutually_exclusive_group(required=True)
    archival_group.add_argument(
        "--stable",
        action="store_const",
        const="git_archival_stable.txt",
        dest="archival_template",
        help="create stable archival file (recommended, no branch names)",
    )
    archival_group.add_argument(
        "--full",
        action="store_const",
        const="git_archival_full.txt",
        dest="archival_template",
        help="create full archival file with branch information (can cause instability)",
    )
    archival_parser.add_argument(
        "--force", action="store_true", help="overwrite existing .git_archival.txt file"
    )
    return parser
