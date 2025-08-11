from __future__ import annotations

import logging
import warnings

from pathlib import Path
from typing import Any
from typing import Callable

import setuptools

from .. import _config
from .pyproject_reading import read_pyproject
from .setup_cfg import _dist_name_from_legacy
from .version_inference import VersionInferenceConfig
from .version_inference import VersionInferenceError
from .version_inference import VersionInferenceException
from .version_inference import get_version_inference_config

log = logging.getLogger(__name__)


def _warn_on_old_setuptools(_version: str = setuptools.__version__) -> None:
    if int(_version.split(".")[0]) < 61:
        warnings.warn(
            RuntimeWarning(
                f"""
ERROR: setuptools=={_version} is used in combination with setuptools-scm>=8.x

Your build configuration is incomplete and previously worked by accident!
setuptools-scm requires setuptools>=61 (recommended: >=80)

Suggested workaround if applicable:
 - migrating from the deprecated setup_requires mechanism to pep517/518
   and using a pyproject.toml to declare build dependencies
   which are reliably pre-installed before running the build tools
"""
            )
        )


def _assign_version(
    dist: setuptools.Distribution, config: _config.Configuration
) -> None:
    from .._get_version_impl import _get_version
    from .._get_version_impl import _version_missing

    # todo: build time plugin
    maybe_version = _get_version(config, force_write_version_files=True)

    if maybe_version is None:
        _version_missing(config)
    else:
        assert dist.metadata.version is None
        dist.metadata.version = maybe_version


_warn_on_old_setuptools()


def _log_hookstart(hook: str, dist: setuptools.Distribution) -> None:
    log.debug("%s %s %s %r", hook, id(dist), id(dist.metadata), vars(dist.metadata))


def get_keyword_overrides(
    value: bool | dict[str, Any] | Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    """normalize the version keyword input"""
    if value is True:
        return {}
    elif callable(value):
        return value()
    else:
        assert isinstance(value, dict), "version_keyword expects a dict or True"
        return value


def version_keyword(
    dist: setuptools.Distribution,
    keyword: str,
    value: bool | dict[str, Any] | Callable[[], dict[str, Any]],
) -> None:
    _log_hookstart("version_keyword", dist)

    # Parse overrides (integration point responsibility)
    overrides = get_keyword_overrides(value)

    assert "dist_name" not in overrides, (
        "dist_name may not be specified in the setup keyword "
    )

    dist_name: str | None = _dist_name_from_legacy(dist)

    was_set_by_infer = getattr(dist, "_setuptools_scm_version_set_by_infer", False)

    # Get pyproject data
    try:
        pyproject_data = read_pyproject(
            Path("pyproject.toml"), missing_section_ok=True, missing_file_ok=True
        )
    except (LookupError, ValueError) as e:
        log.debug("Configuration issue in pyproject.toml: %s", e)
        return

    # Get decision
    result = get_version_inference_config(
        dist_name=dist_name,
        current_version=dist.metadata.version,
        pyproject_data=pyproject_data,
        overrides=overrides,
        was_set_by_infer=was_set_by_infer,
    )

    # Handle result
    if result is None:
        return  # Don't infer
    elif isinstance(result, VersionInferenceError):
        if result.should_warn:
            warnings.warn(result.message)
        return
    elif isinstance(result, VersionInferenceException):
        raise result.exception
    elif isinstance(result, VersionInferenceConfig):
        # Clear version if it was set by infer_version
        if was_set_by_infer:
            dist._setuptools_scm_version_set_by_infer = False  # type: ignore[attr-defined]
            dist.metadata.version = None

        # Proceed with inference
        config = _config.Configuration.from_file(
            dist_name=result.dist_name,
            pyproject_data=result.pyproject_data,
            missing_file_ok=True,
            missing_section_ok=True,
            **overrides,
        )
        _assign_version(dist, config)


def infer_version(dist: setuptools.Distribution) -> None:
    _log_hookstart("infer_version", dist)

    dist_name = _dist_name_from_legacy(dist)

    # Get pyproject data (integration point responsibility)
    try:
        pyproject_data = read_pyproject(Path("pyproject.toml"), missing_section_ok=True)
    except FileNotFoundError:
        log.debug("pyproject.toml not found, skipping infer_version")
        return
    except (LookupError, ValueError) as e:
        log.debug("Configuration issue in pyproject.toml: %s", e)
        return

    # Get decision
    result = get_version_inference_config(
        dist_name=dist_name,
        current_version=dist.metadata.version,
        pyproject_data=pyproject_data,
    )

    # Handle result
    if result is None:
        return  # Don't infer
    elif isinstance(result, VersionInferenceError):
        if result.should_warn:
            log.warning(result.message)
        return
    elif isinstance(result, VersionInferenceException):
        raise result.exception
    elif isinstance(result, VersionInferenceConfig):
        # Proceed with inference
        try:
            config = _config.Configuration.from_file(
                dist_name=result.dist_name, pyproject_data=result.pyproject_data
            )
        except LookupError as e:
            log.info(e, exc_info=True)
        else:
            _assign_version(dist, config)
            # Mark that this version was set by infer_version
            dist._setuptools_scm_version_set_by_infer = True  # type: ignore[attr-defined]
