"""Workdir discovery: probe directories for SCM or fallback workdirs.

``discover_workdir`` uses a two-phase algorithm, calling registered factory
entry points from the ``vcs_versioning.discover_workdir`` group:

1. **SCM phase** — probe ``absolute_root`` (and parent directories when
   ``search_parent_directories`` is enabled) for live VCS checkouts.
2. **Fallback phase** — if no SCM workdir was found, probe the project
   directory (where ``relative_to`` / pyproject.toml lives) for fallback
   workdirs only (archival files, egg-info metadata, etc.).

SCM results are preferred over fallback results.
"""

from __future__ import annotations

import logging
from importlib.metadata import entry_points
from pathlib import Path
from typing import Protocol

from ._backends._scm_workdir import ScmWorkdir
from ._config import Configuration
from ._fallback_workdir import FallbackWorkdir, StaticWorkdir

log = logging.getLogger(__name__)

AnyWorkdir = ScmWorkdir | FallbackWorkdir


class DiscoveryFactory(Protocol):
    def __call__(
        self, path: Path, *, config: Configuration
    ) -> ScmWorkdir | FallbackWorkdir | None: ...


def _verify_project_path(workdir: ScmWorkdir, config: Configuration) -> bool:
    """Check that the discovered project_path matches the configured one."""
    if config.project_path is None:
        return True
    if workdir.project_path == config.project_path:
        return True
    log.warning(
        "project_path mismatch: config declares %r but discovery found %r",
        config.project_path,
        workdir.project_path,
    )
    return False


def _load_discovery_factories() -> list[tuple[str, DiscoveryFactory]]:
    """Load all factories from ``vcs_versioning.discover_workdir`` EPs."""
    eps = entry_points(group="vcs_versioning.discover_workdir")
    result: list[tuple[str, DiscoveryFactory]] = []
    for ep in eps:
        try:
            factory: DiscoveryFactory = ep.load()
            result.append((ep.name, factory))
        except Exception:
            log.warning("failed to load discovery EP %s", ep.name, exc_info=True)
    return result


def discover_workdir(config: Configuration) -> AnyWorkdir | None:
    """Discover the workdir for the given configuration.

    Algorithm:
    0. If config.parse is set, return a LegacyParseWorkdir (deprecated path).
    1. SCM phase: probe ``absolute_root`` (and parents when enabled).
       - ScmWorkdir result: verify project_path, return immediately.
       - FallbackWorkdir result: stash as candidate, keep probing for SCM.
    2. Fallback phase: probe ``project_dir`` (if different from scm root).
    3. Return best stashed FallbackWorkdir if no SCM found.
    4. Try StaticWorkdir from config.fallback_version / parentdir_prefix_version.
    5. Return None.
    """
    if config.parse is not None:
        from ._legacy_parse import LegacyParseWorkdir

        log.info("using LegacyParseWorkdir for config.parse (deprecated)")
        return LegacyParseWorkdir(
            path=Path(config.absolute_root),
            _config=config,
            _parse_fn=config.parse,
        )

    factories = _load_discovery_factories()
    if not factories:
        log.debug("no discovery factories registered")

    # Use the canonical path resolution from config.
    project_dir = config._resolved_paths.project_dir
    scm_root_hint = config._resolved_paths.scm_probe_root

    fallback_candidate: FallbackWorkdir | None = None

    def _accept_scm(result: ScmWorkdir, ep_name: str) -> ScmWorkdir:
        result.project_root = project_dir
        result._config = config
        if not _verify_project_path(result, config):
            raise ValueError(
                f"project_path mismatch: config declares "
                f"{config.project_path!r} but SCM root at {result.path} "
                f"yields {result.project_path!r}"
            )
        log.info(
            "discovered SCM workdir %s (factory=%s)", type(result).__name__, ep_name
        )
        return result

    def _probe_dir(current_dir: Path, *, accept_scm: bool) -> ScmWorkdir | None:
        nonlocal fallback_candidate
        for ep_name, factory in factories:
            try:
                result = factory(current_dir, config=config)
            except Exception:
                log.debug(
                    "factory %s raised at %s", ep_name, current_dir, exc_info=True
                )
                continue
            if result is None:
                continue
            if accept_scm and isinstance(result, ScmWorkdir):
                return _accept_scm(result, ep_name)
            if isinstance(result, FallbackWorkdir) and fallback_candidate is None:
                result._config = config
                log.debug(
                    "stashed fallback workdir %s from factory %s at %s",
                    type(result).__name__,
                    ep_name,
                    current_dir,
                )
                fallback_candidate = result
        return None

    # Phase 1: SCM probes at scm_root_hint (the declared root) and optionally parents.
    scm_dirs: list[Path] = [scm_root_hint]
    if config.search_parent_directories:
        scm_dirs.extend(scm_root_hint.parents)
    for d in scm_dirs:
        scm = _probe_dir(d, accept_scm=True)
        if scm is not None:
            return scm

    # Phase 2: Fallback probes at project_dir (if different from scm_root_hint).
    if project_dir != scm_root_hint:
        _probe_dir(project_dir, accept_scm=False)

    if fallback_candidate is not None:
        log.info("using fallback workdir %s", type(fallback_candidate).__name__)
        return fallback_candidate

    static = StaticWorkdir(path=project_dir, _config=config)
    if static.get_scm_version() is not None:
        log.info("using static fallback workdir")
        return static

    return None
