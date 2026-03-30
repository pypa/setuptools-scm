"""Read/write SCM metadata in JSON format.

Two files are used:
- ``scm_version.json`` -- tag, distance, node, dirty, branch, node_date
- ``scm_file_list.json`` -- tracked file list

The format is defined here in vcs-versioning; where the files are placed
(e.g. inside egg-info for setuptools) is up to each build backend.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

SCM_VERSION_FILENAME = "scm_version.json"
SCM_FILE_LIST_FILENAME = "scm_file_list.json"


@dataclass(frozen=True)
class ScmVersionData:
    """Serializable SCM version metadata."""

    tag: str
    distance: int
    node: str | None
    dirty: bool
    branch: str | None
    node_date: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_scm_version_data(target_dir: Path, data: ScmVersionData) -> Path:
    """Write ``scm_version.json`` into *target_dir*."""
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / SCM_VERSION_FILENAME
    path.write_text(json.dumps(data.to_dict(), indent=2) + "\n", encoding="utf-8")
    log.debug("wrote %s", path)
    return path


def read_scm_version_data(source_dir: Path) -> ScmVersionData | None:
    """Read ``scm_version.json`` from *source_dir*, returning ``None`` if absent."""
    path = source_dir / SCM_VERSION_FILENAME
    if not path.is_file():
        return None
    try:
        raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return ScmVersionData(
            tag=raw["tag"],
            distance=int(raw["distance"]),
            node=raw.get("node"),
            dirty=bool(raw.get("dirty", False)),
            branch=raw.get("branch"),
            node_date=raw.get("node_date"),
        )
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        log.warning("failed to read %s: %s", path, exc)
        return None


def write_scm_file_list(target_dir: Path, files: list[str]) -> Path:
    """Write ``scm_file_list.json`` into *target_dir*."""
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / SCM_FILE_LIST_FILENAME
    payload = {"files": files}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    log.debug("wrote %s", path)
    return path


def read_scm_file_list(source_dir: Path) -> list[str] | None:
    """Read ``scm_file_list.json`` from *source_dir*, returning ``None`` if absent."""
    path = source_dir / SCM_FILE_LIST_FILENAME
    if not path.is_file():
        return None
    try:
        raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return list(raw["files"])
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        log.warning("failed to read %s: %s", path, exc)
        return None


def scm_version_data_from_scm_version(
    scm_version: Any,
) -> ScmVersionData:
    """Build ``ScmVersionData`` from a live ``ScmVersion`` object.

    Accepts ``Any`` to avoid a circular import with ``_scm_version``.
    """
    raw_date = scm_version.node_date
    return ScmVersionData(
        tag=str(scm_version.tag),
        distance=scm_version.distance,
        node=scm_version.node,
        dirty=scm_version.dirty,
        branch=scm_version.branch,
        node_date=raw_date.isoformat() if isinstance(raw_date, date) else None,
    )
