from __future__ import annotations

import json
import os
import sys
from collections.abc import MutableMapping
from importlib.resources import files
from pathlib import Path
from typing import Any

from .. import _discover as discover
from .._config import Configuration
from .._get_version_impl import _get_version
from .._pyproject_reading import PyProjectData
from ._args import CliNamespace, get_cli_parser


def _get_version_for_cli(config: Configuration, opts: CliNamespace) -> str:
    """Get version string for CLI output, handling special cases and exceptions."""
    if opts.no_version:
        return "0.0.0+no-version-was-requested.fake-version"

    version = _get_version(
        config, force_write_version_files=opts.force_write_version_files
    )
    if version is None:
        raise SystemExit("ERROR: no version found for", opts)

    if opts.strip_dev:
        version = version.partition(".dev")[0]

    return version


def main(
    args: list[str] | None = None, *, _given_pyproject_data: PyProjectData | None = None
) -> int:
    from ..overrides import GlobalOverrides

    # Apply global overrides for the entire CLI execution
    # Logging is automatically configured when entering the context
    with GlobalOverrides.from_env("SETUPTOOLS_SCM"):
        parser = get_cli_parser("python -m vcs_versioning")
        opts = parser.parse_args(args, namespace=CliNamespace())
        inferred_root: str = opts.root or "."

        pyproject = opts.config or _find_pyproject(inferred_root)

        try:
            config = Configuration.from_file(
                pyproject,
                root=(os.path.abspath(opts.root) if opts.root is not None else None),
                pyproject_data=_given_pyproject_data,
            )
        except (LookupError, FileNotFoundError) as ex:
            # no pyproject.toml OR no [tool.setuptools_scm]
            print(
                f"Warning: could not use {os.path.relpath(pyproject)},"
                " using default configuration.\n"
                f" Reason: {ex}.",
                file=sys.stderr,
            )
            config = Configuration(root=inferred_root)

        version = _get_version_for_cli(config, opts)
        return command(opts, version, config)


# flake8: noqa: C901
def command(opts: CliNamespace, version: str, config: Configuration) -> int:
    data: dict[str, Any] = {}

    if opts.command == "ls":
        opts.query = ["files"]

    if opts.command == "create-archival-file":
        return _create_archival_file(opts, config)

    if opts.query == []:
        opts.no_version = True
        sys.stderr.write("Available queries:\n\n")
        opts.query = ["queries"]
        data["queries"] = ["files", *config.__dataclass_fields__]

    if opts.query is None:
        opts.query = []

    if not opts.no_version:
        data["version"] = version

    if "files" in opts.query:
        from .._file_finders import find_files

        data["files"] = find_files(config.root)

    for q in opts.query:
        if q in ["files", "queries", "version"]:
            continue

        try:
            if q.startswith("_"):
                raise AttributeError()
            data[q] = getattr(config, q)
        except AttributeError:
            sys.stderr.write(f"Error: unknown query: '{q}'\n")
            return 1

    PRINT_FUNCTIONS[opts.format](data)

    return 0


def print_json(data: MutableMapping[str, Any]) -> None:
    print(json.dumps(data, indent=2))


def print_plain(data: MutableMapping[str, Any]) -> None:
    version = data.pop("version", None)
    if version:
        print(version)
    files = data.pop("files", [])
    for file_ in files:
        print(file_)
    queries = data.pop("queries", [])
    for query in queries:
        print(query)
    if data:
        print("\n".join(data.values()))


def print_key_value(data: MutableMapping[str, Any]) -> None:
    for key, value in data.items():
        if isinstance(value, str):
            print(f"{key} = {value}")
        else:
            str_value = "\n  ".join(value)
            print(f"{key} = {str_value}")


PRINT_FUNCTIONS = {
    "json": print_json,
    "plain": print_plain,
    "key-value": print_key_value,
}


def _find_pyproject(parent: str) -> str:
    for directory in discover.walk_potential_roots(os.path.abspath(parent)):
        pyproject = os.path.join(directory, "pyproject.toml")
        if os.path.isfile(pyproject):
            return pyproject

    return os.path.abspath(
        "pyproject.toml"
    )  # use default name to trigger the default errors


def _create_archival_file(opts: CliNamespace, config: Configuration) -> int:
    """Create .git_archival.txt file with appropriate content."""
    archival_path = Path(config.root, ".git_archival.txt")

    # Check if file exists and force flag
    if archival_path.exists() and not opts.force:
        print(
            f"Error: {archival_path} already exists. Use --force to overwrite.",
            file=sys.stderr,
        )
        return 1

    # archival_template is guaranteed to be set by required mutually exclusive group
    assert opts.archival_template is not None

    # Load template content from package resources
    content = files(__package__).joinpath(opts.archival_template).read_text("utf-8")

    # Print appropriate message based on template
    if opts.archival_template == "git_archival_stable.txt":
        print("Creating stable .git_archival.txt (recommended for releases)")
    elif opts.archival_template == "git_archival_full.txt":
        print("Creating full .git_archival.txt with branch information")
        print("WARNING: This can cause archive checksums to be unstable!")

    try:
        archival_path.write_text(content, encoding="utf-8")
        print(f"Created: {archival_path}")

        gitattributes_path = Path(config.root, ".gitattributes")
        needs_gitattributes = True

        if gitattributes_path.exists():
            # TODO: more nuanced check later
            gitattributes_content = gitattributes_path.read_text("utf-8")
            if (
                ".git_archival.txt" in gitattributes_content
                and "export-subst" in gitattributes_content
            ):
                needs_gitattributes = False

        if needs_gitattributes:
            print("\nNext steps:")
            print("1. Add this line to .gitattributes:")
            print("   .git_archival.txt  export-subst")
            print("2. Commit both files:")
            print("   git add .git_archival.txt .gitattributes")
            print("   git commit -m 'add git archive support'")
        else:
            print("\nNext step:")
            print("Commit the archival file:")
            print("   git add .git_archival.txt")
            print("   git commit -m 'update git archival file'")

        return 0
    except OSError as e:
        print(f"Error: Could not create {archival_path}: {e}", file=sys.stderr)
        return 1
