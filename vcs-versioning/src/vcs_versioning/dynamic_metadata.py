"""scikit-build ``dynamic-metadata`` provider for vcs-versioning.

Use this module as a provider for `scikit-build/dynamic-metadata
<https://github.com/scikit-build/dynamic-metadata>`_ so any backend supporting
that can fill in a VCS-derived ``version``::

    [[tool.dynamic-metadata]]
    provider = "vcs_versioning.dynamic_metadata"

Configuration is read from ``[tool.vcs-versioning]``; any keys in the
``[[tool.dynamic-metadata]]`` table are passed through as overrides.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

from vcs_versioning import PyProjectData, infer_version_string
from vcs_versioning.overrides import GlobalOverrides

__all__ = ["dynamic_metadata"]


def __dir__() -> list[str]:
    return __all__


def dynamic_metadata(
    settings: Mapping[str, Any],
    project: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the ``version`` field for a dynamic-metadata consumer."""
    dist_name = project.get("name")
    # dynamic-metadata runs hooks with cwd at the project root.
    with GlobalOverrides.from_env("VCS_VERSIONING", dist_name=dist_name):
        pyproject = PyProjectData.from_file("pyproject.toml")
        version = infer_version_string(
            dist_name=dist_name,
            pyproject_data=pyproject,
            overrides=dict(settings) or None,
            force_write_version_files=True,
        )
    return {"version": version}
