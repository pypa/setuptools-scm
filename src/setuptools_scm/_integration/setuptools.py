from __future__ import annotations

import logging
import warnings

from pathlib import Path
from typing import Any
from typing import Callable

import setuptools

from .. import _types as _t
from .pyproject_reading import PyProjectData
from .pyproject_reading import read_pyproject
from .setup_cfg import extract_from_legacy
from .toml import InvalidTomlError
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


_warn_on_old_setuptools()


def _log_hookstart(hook: str, dist: setuptools.Distribution) -> None:
    log.debug(
        "%s %s %s %r",
        hook,
        id(dist),
        id(dist.metadata),
        {**vars(dist.metadata), "long_description": ...},
    )


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
    *,
    _given_pyproject_data: _t.GivenPyProjectResult = None,
    _get_version_inference_config: _t.GetVersionInferenceConfig = get_version_inference_config,
) -> None:
    """apply version infernce when setup(use_scm_version=...) is used
    this takes priority over the finalize_options based version
    """

    _log_hookstart("version_keyword", dist)

    # Parse overrides (integration point responsibility)
    overrides = get_keyword_overrides(value)

    assert "dist_name" not in overrides, (
        "dist_name may not be specified in the setup keyword "
    )

    legacy_data = extract_from_legacy(dist)
    dist_name: str | None = legacy_data.name

    was_set_by_infer = getattr(dist, "_setuptools_scm_version_set_by_infer", False)

    # Get pyproject data (support direct injection for tests)
    try:
        pyproject_data = read_pyproject(_given_result=_given_pyproject_data)
    except FileNotFoundError:
        log.debug("pyproject.toml not found, proceeding with empty configuration")
        pyproject_data = PyProjectData.empty(Path("pyproject.toml"), "setuptools_scm")
    except InvalidTomlError as e:
        log.debug("Configuration issue in pyproject.toml: %s", e)
        return

    result = _get_version_inference_config(
        dist_name=dist_name,
        current_version=legacy_data.version or pyproject_data.project.get("version"),
        pyproject_data=pyproject_data,
        overrides=overrides,
        was_set_by_infer=was_set_by_infer,
    )

    result.apply(dist)


def infer_version(
    dist: setuptools.Distribution,
    *,
    _given_pyproject_data: _t.GivenPyProjectResult = None,
    _get_version_inference_config: _t.GetVersionInferenceConfig = get_version_inference_config,
) -> None:
    """apply version inference from the finalize_options hook
    this is the default for pyproject.toml based projects that don't use the use_scm_version keyword

    if the version keyword is used, it will override the version from this hook
    as user might have passed custom code version schemes
    """

    _log_hookstart("infer_version", dist)

    legacy_data = extract_from_legacy(dist)
    dist_name = legacy_data.name

    try:
        pyproject_data = read_pyproject(_given_result=_given_pyproject_data)
    except FileNotFoundError:
        log.debug("pyproject.toml not found, skipping infer_version")
        return
    except InvalidTomlError as e:
        log.debug("Configuration issue in pyproject.toml: %s", e)
        return

    # Only infer when tool section present per get_version_inference_config
    result = _get_version_inference_config(
        dist_name=dist_name,
        current_version=legacy_data.version or pyproject_data.project.get("version"),
        pyproject_data=pyproject_data,
    )
    result.apply(dist)
