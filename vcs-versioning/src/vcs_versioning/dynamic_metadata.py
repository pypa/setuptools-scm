"""scikit-build ``dynamic-metadata`` provider for vcs-versioning.

Use this module as a provider for `scikit-build/dynamic-metadata
<https://github.com/scikit-build/dynamic-metadata>`_ so any PEP 517 backend can
fill in a VCS-derived ``version``::

    [[tool.dynamic-metadata]]
    provider = "vcs_versioning.dynamic_metadata"
    field = "version"

Configuration is read from ``[tool.vcs-versioning]``; extra keys in the
``[[tool.dynamic-metadata]]`` table (anything besides ``field``) are passed
through as overrides.

This targets the current standalone ``dynamic-metadata`` signature
(``dynamic_metadata(settings, project)``); it is not the same protocol as
scikit-build-core's built-in ``dynamic_metadata(field, settings)`` loader.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = ["dynamic_metadata", "get_requires_for_dynamic_metadata"]


def __dir__() -> list[str]:
    return __all__


def dynamic_metadata(
    settings: Mapping[str, Any],
    project: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the ``version`` field for a dynamic-metadata consumer."""
    from vcs_versioning import PyProjectData, infer_version_string
    from vcs_versioning.overrides import GlobalOverrides

    field = settings.get("field", "version")
    if field != "version":
        raise ValueError(
            "vcs-versioning dynamic-metadata provider only supports the"
            f" 'version' field, got {field!r}"
        )
    # Everything except `field` becomes a config override (e.g. local_scheme).
    overrides = {k: v for k, v in settings.items() if k != "field"}

    dist_name = project.get("name")
    # dynamic-metadata runs hooks with cwd at the project root.
    with GlobalOverrides.from_env("VCS_VERSIONING", dist_name=dist_name):
        pyproject = PyProjectData.from_file("pyproject.toml")
        version = infer_version_string(
            dist_name=dist_name,
            pyproject_data=pyproject,
            overrides=overrides or None,
            force_write_version_files=True,
        )
    return {field: version}


def get_requires_for_dynamic_metadata(
    _settings: Mapping[str, Any],
) -> list[str]:
    """Inject vcs-versioning as a build requirement."""
    return ["vcs-versioning"]
