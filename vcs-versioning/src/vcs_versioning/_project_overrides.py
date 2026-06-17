"""Per-project overrides from ``.config/python-vcs-versioning.toml``.

.. note:: **Not yet wired into production code.**

   This module is reserved for a future feature.  It is tested
   (``testing_vcs/test_project_overrides.py``) but not imported by any
   production path (``Configuration.from_file``, ``build_configuration_from_pyproject_internal``,
   or ``discover_workdir``).  The integration point will be determined once
   the linear ``env -> config -> workdir -> version`` pipeline is finalised.

Located in the SCM root, this file allows vendored or deeply-nested projects
to have independent configuration without modifying their own pyproject.toml.

Format::

    ["python/modules/mymodule"]
    version_scheme = "calver-by-date"
    tag_regex = "mymodule-v*"
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

CONFIG_FILENAME = ".config/python-vcs-versioning.toml"

ALLOWED_OVERRIDE_KEYS: frozenset[str] = frozenset(
    {
        "version_scheme",
        "local_scheme",
        "tag_regex",
        "parentdir_prefix_version",
        "fallback_version",
        "fallback_root",
        "write_to",
        "write_to_template",
        "version_file",
        "version_file_template",
        "dist_name",
        "search_parent_directories",
    }
)


def read_project_overrides(scm_root: Path, project_path: str) -> dict[str, Any]:
    """Read per-project overrides from the SCM root config file.

    Args:
        scm_root: The VCS checkout root directory.
        project_path: The relative path of the project within the checkout
                      (empty string for top-level projects).

    Returns:
        A dictionary of configuration overrides, or empty dict if none found.

    Raises:
        ValueError: If the override file contains unknown keys.
    """
    config_file = scm_root / CONFIG_FILENAME
    if not config_file.is_file():
        return {}

    try:
        from ._toml import read_toml_content

        data = read_toml_content(config_file)
    except Exception:
        log.warning("failed to read %s", config_file, exc_info=True)
        return {}

    key = project_path if project_path else "."
    overrides = data.get(key, {})
    if not isinstance(overrides, dict):
        log.warning(
            "expected table for key %r in %s, got %s",
            key,
            config_file,
            type(overrides).__name__,
        )
        return {}

    unknown_keys = set(overrides) - ALLOWED_OVERRIDE_KEYS
    if unknown_keys:
        raise ValueError(
            f"Unknown keys in {config_file} [{key}]: {sorted(unknown_keys)}. "
            f"Allowed keys: {sorted(ALLOWED_OVERRIDE_KEYS)}"
        )

    if overrides:
        log.info(
            "loaded per-project overrides for %r from %s: %s",
            key,
            config_file,
            overrides,
        )
    return dict(overrides)
