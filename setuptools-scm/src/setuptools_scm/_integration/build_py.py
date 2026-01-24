"""Custom build_py command that writes version files to the build directory.

This module provides a custom build_py command that writes version files
to the build directory (self.build_lib) instead of the source tree.
This supports read-only source installations (e.g., Bazel builds).
"""

from __future__ import annotations

import logging

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from setuptools.command.build_py import build_py as _build_py

if TYPE_CHECKING:
    from setuptools import Distribution
    from vcs_versioning import Configuration
    from vcs_versioning import ScmVersion

log = logging.getLogger(__name__)


def _transform_version_file_path(
    version_file: str, package_dir: dict[str, str] | None
) -> str:
    """Transform version_file path based on package_dir mapping.

    For src/ layouts, strips the source directory prefix so the path
    is relative to the package root in the build directory.

    Examples:
        version_file='src/mypackage/_version.py' + package_dir={'': 'src'}
        -> 'mypackage/_version.py'

        version_file='mypackage/_version.py' + package_dir=None
        -> 'mypackage/_version.py' (unchanged)

    Args:
        version_file: The configured version file path (relative to project root)
        package_dir: The package_dir mapping from setuptools configuration

    Returns:
        The transformed path suitable for the build directory
    """
    if not package_dir:
        return version_file

    version_path = Path(version_file)

    # Check the root package_dir mapping (empty string key)
    # This handles the common case: package_dir = {"": "src"}
    root_dir = package_dir.get("", "")
    if root_dir:
        root_path = Path(root_dir)
        try:
            relative = version_path.relative_to(root_path)
            log.debug(
                "Transformed version file path: %s -> %s (stripped %s)",
                version_file,
                relative,
                root_dir,
            )
            return str(relative)
        except ValueError:
            pass  # Not relative to root_dir

    # Check other package mappings (e.g., {"mypackage": "lib"})
    for pkg_name, pkg_dir in package_dir.items():
        if pkg_name == "":
            continue
        pkg_path = Path(pkg_dir)
        try:
            relative = version_path.relative_to(pkg_path)
            # Replace pkg_dir prefix with pkg_name
            result = str(Path(pkg_name.replace(".", "/")) / relative)
            log.debug(
                "Transformed version file path: %s -> %s (pkg %s -> %s)",
                version_file,
                result,
                pkg_dir,
                pkg_name,
            )
            return result
        except ValueError:
            pass

    # No transformation needed
    return version_file


@dataclass(frozen=True)
class VersionInferenceData:
    """Data from version inference stored on the distribution.

    Contains the Configuration and ScmVersion objects needed by
    the build_py command to write version files to the build directory.
    """

    version: str
    """The computed version string."""

    config: Configuration
    """The full Configuration object."""

    scm_version: ScmVersion | None
    """The ScmVersion object (may be None if from fallback/pretend)."""


def get_version_inference_data(dist: Distribution) -> VersionInferenceData | None:
    """Get the version inference data from the distribution.

    Returns None if no data was stored.
    """
    return getattr(dist, "_setuptools_scm_version_inference_data", None)


def set_version_inference_data(dist: Distribution, data: VersionInferenceData) -> None:
    """Store the version inference data on the distribution."""
    dist._setuptools_scm_version_inference_data = data  # type: ignore[attr-defined]


class build_py(_build_py):
    """Custom build_py that writes version files to the build directory.

    This command extends the standard build_py to write version files
    (like _version.py) to self.build_lib instead of the source tree.
    This enables installing packages from read-only source directories.
    """

    def run(self) -> None:
        """Run the build_py command and write version files to build_lib."""
        # First, run the standard build_py to copy files
        super().run()

        # Then write version files to the build directory
        self._write_version_files()

    def _write_version_files(self) -> None:
        """Write version files to the build directory."""
        data = get_version_inference_data(self.distribution)
        if data is None:
            log.debug("No version inference data found, skipping version file writing")
            return

        config = data.config
        if config.write_to is None and config.version_file is None:
            log.debug("No version file paths configured, skipping")
            return

        build_lib = Path(self.build_lib)
        log.info("Writing version files to build directory: %s", build_lib)

        # Get package_dir mapping for path transformation (handles src/ layouts)
        package_dir = getattr(self.distribution, "package_dir", None)

        # Handle legacy write_to
        if config.write_to:
            transformed_path = _transform_version_file_path(
                str(config.write_to), package_dir
            )
            self._write_single_version_file(
                build_lib=build_lib,
                relative_path=transformed_path,
                template=config.write_to_template,
                version=data.version,
                scm_version=data.scm_version,
            )

        # Handle new version_file
        if config.version_file:
            transformed_path = _transform_version_file_path(
                str(config.version_file), package_dir
            )
            self._write_single_version_file(
                build_lib=build_lib,
                relative_path=transformed_path,
                template=config.version_file_template,
                version=data.version,
                scm_version=data.scm_version,
            )

    def _write_single_version_file(
        self,
        build_lib: Path,
        relative_path: str,
        template: str | None,
        version: str,
        scm_version: Any,
    ) -> None:
        """Write a single version file to the build directory."""
        from vcs_versioning._dump_version import DummyScmVersion
        from vcs_versioning._dump_version import _validate_template
        from vcs_versioning._version_cls import _version_as_tuple

        target = build_lib / relative_path
        log.debug("Writing version file: %s", target)

        try:
            final_template = _validate_template(target, template)
        except ValueError as e:
            log.warning("Skipping version file %s: %s", target, e)
            return

        version_tuple = _version_as_tuple(version)
        content = final_template.format(
            version=version,
            version_tuple=version_tuple,
            scm_version=scm_version or DummyScmVersion(),
        )

        # Ensure parent directory exists
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        log.info("Wrote version file: %s", target)
