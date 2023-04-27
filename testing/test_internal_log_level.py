from __future__ import annotations

import logging

from setuptools_scm import _log


def test_log_levels_when_set() -> None:
    assert _log._default_log_level({"SETUPTOOLS_SCM_DEBUG": ""}) == logging.DEBUG
    assert _log._default_log_level({"SETUPTOOLS_SCM_DEBUG": "INFO"}) == logging.DEBUG
    assert _log._default_log_level({"SETUPTOOLS_SCM_DEBUG": "3"}) == logging.DEBUG


def test_log_levels_when_unset() -> None:
    assert _log._default_log_level({}) == logging.WARNING
