"""
this module is a hack only in place to allow for setuptools
to use the attribute for the versions
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

root = Path(__file__).parent
sys.path.insert(0, os.fspath(root / "src"))

from setuptools.build_meta import (  # type: ignore[attr-defined]
    get_requires_for_build_wheel,
    get_requires_for_build_sdist,
    prepare_metadata_for_build_wheel,
    build_wheel,
    build_sdist,
    get_requires_for_build_editable,
    prepare_metadata_for_build_editable,
    build_editable,
)


from setuptools_scm import get_version
from setuptools_scm.hacks import parse_pkginfo
from setuptools_scm import git
from setuptools_scm import hg
from setuptools_scm.version import guess_next_dev_version, get_local_node_and_date
from setuptools_scm import Configuration

from setuptools_scm.version import ScmVersion


dynamic_version: str


def parse(root: str, config: Configuration) -> ScmVersion | None:
    try:
        return parse_pkginfo(root, config)
    except OSError:
        return git.parse(root, config=config) or hg.parse(root, config=config)


def scm_version() -> str:
    return get_version(
        root=str(root),
        parse=parse,
        version_scheme=guess_next_dev_version,
        local_scheme=get_local_node_and_date,
    )


def __getattr__(name: str) -> str:
    if name == "dynamic_version":
        global dynamic_version
        dynamic_version = scm_version()
        return dynamic_version
    raise AttributeError(name)
