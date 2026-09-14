"""Verify setuptools-scm imports cleanly against its declared vcs-versioning floor.

setuptools-scm consumes vcs-versioning's private modules, so the declared lower
bound is a real compatibility claim rather than a formality.  Nothing in the
normal test matrix exercises it: every job resolves the newest vcs-versioning,
so a floor that has silently gone stale still goes green.  setuptools-scm 10.3.0
shipped that way -- it imports ``vcs_versioning._file_finders.scm_search_known_failed``,
added in vcs-versioning 2.4.0, while declaring ``>=2.3.2.dev0``.

This check installs the built wheel, forces vcs-versioning down to the oldest
published release the wheel's metadata permits, and imports every
``setuptools_scm`` submodule.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

CORE = "vcs-versioning"

# Imports every submodule so that a missing private name fails here rather than
# in a user's build.  Printed names are the failures, one per line.
_IMPORT_PROBE = """
import importlib
import pkgutil

import setuptools_scm

for module in pkgutil.walk_packages(setuptools_scm.__path__, "setuptools_scm."):
    try:
        importlib.import_module(module.name)
    except Exception as exc:  # noqa: BLE001 - report, do not raise
        print(f"{module.name}: {type(exc).__name__}: {exc}")
"""


def core_specifier(wheel: Path) -> SpecifierSet:
    """Read the vcs-versioning requirement out of a built wheel's metadata."""
    with zipfile.ZipFile(wheel) as archive:
        name = next(n for n in archive.namelist() if n.endswith(".dist-info/METADATA"))
        metadata = archive.read(name).decode()

    for line in metadata.splitlines():
        if not line.startswith("Requires-Dist:"):
            continue
        requirement = Requirement(line.partition(":")[2].strip())
        if requirement.name == CORE:
            return requirement.specifier
    raise SystemExit(f"{wheel.name} declares no {CORE} dependency")


def published_versions(package: str) -> list[Version]:
    """Published, non-yanked releases of ``package`` on PyPI, oldest first."""
    url = f"https://pypi.org/pypi/{package}/json"
    with urllib.request.urlopen(url) as response:
        data = json.load(response)

    versions = [
        Version(version)
        for version, files in data["releases"].items()
        if files and not all(file["yanked"] for file in files)
    ]
    return sorted(versions)


def oldest_permitted(specifier: SpecifierSet) -> Version | None:
    """Oldest published release satisfying ``specifier``, or None if there is none.

    None is the normal state for the change that *raises* the floor: it names the
    next vcs-versioning version, which is not on PyPI until the release lands.
    A floor that has gone stale still points at a published version, so the case
    this check exists for is the case that does resolve.
    """
    permitted = [v for v in published_versions(CORE) if specifier.contains(v)]
    return permitted[0] if permitted else None


def run(*command: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(part) for part in command], capture_output=True, text=True, check=False
    )


def check(wheel: Path, python_version: str) -> int:
    specifier = core_specifier(wheel)
    floor = oldest_permitted(specifier)
    if floor is None:
        print(
            f"{wheel.name} declares {CORE}{specifier}, which no published release"
            f" satisfies yet -- nothing to check until that {CORE} is released."
        )
        return 0
    print(f"{wheel.name} declares {CORE}{specifier}; oldest published match: {floor}")

    with tempfile.TemporaryDirectory() as tmp:
        venv = Path(tmp) / "venv"
        steps = [
            ("create venv", ("uv", "venv", "-q", venv, "--python", python_version)),
            (
                "install wheel",
                ("uv", "pip", "install", "-q", "-p", venv, wheel, "setuptools"),
            ),
            # --no-deps so the wheel's own floor cannot pull the core back up.
            (
                "pin core to floor",
                (
                    "uv",
                    "pip",
                    "install",
                    "-q",
                    "-p",
                    venv,
                    "--no-deps",
                    f"{CORE}=={floor}",
                ),
            ),
        ]
        for label, command in steps:
            result = run(*command)
            if result.returncode:
                print(f"failed to {label}:\n{result.stderr}", file=sys.stderr)
                return 1

        probe = run(venv / "bin" / "python", "-c", _IMPORT_PROBE)
        failures = [line for line in probe.stdout.splitlines() if line.strip()]

    if failures:
        print(
            f"\nsetuptools-scm does not import against {CORE} {floor},"
            f" its own declared floor:\n",
            file=sys.stderr,
        )
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        print(
            f"\nRaise the {CORE} lower bound in setuptools-scm/pyproject.toml"
            " (both build-system.requires and project.dependencies).",
            file=sys.stderr,
        )
        return 1

    print(f"ok: setuptools-scm imports cleanly against {CORE} {floor}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "wheel",
        type=Path,
        help="built setuptools-scm wheel, or a directory holding one",
    )
    parser.add_argument(
        "--python", default="3.12", help="python version for the probe venv"
    )
    args = parser.parse_args()

    wheel: Path = args.wheel
    if wheel.is_dir():
        candidates = sorted(wheel.glob("setuptools_scm-*.whl"))
        if not candidates:
            raise SystemExit(f"no setuptools-scm wheel in {wheel}")
        wheel = candidates[0]

    return check(wheel, args.python)


if __name__ == "__main__":
    raise SystemExit(main())
