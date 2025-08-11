from __future__ import annotations

import os

import setuptools


def read_dist_name_from_setup_cfg(
    input: str | os.PathLike[str] = "setup.cfg",
) -> str | None:
    # minimal effort to read dist_name off setup.cfg metadata
    import configparser

    parser = configparser.ConfigParser()
    parser.read([input], encoding="utf-8")
    dist_name = parser.get("metadata", "name", fallback=None)
    return dist_name


def _dist_name_from_legacy(dist: setuptools.Distribution) -> str | None:
    return dist.metadata.name or read_dist_name_from_setup_cfg()
