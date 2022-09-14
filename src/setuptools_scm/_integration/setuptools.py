from __future__ import annotations

import os


def read_dist_name_from_setup_cfg(
    input: str | os.PathLike[str] = "setup.cfg",
) -> str | None:

    # minimal effort to read dist_name off setup.cfg metadata
    import configparser

    parser = configparser.ConfigParser()
    parser.read([input])
    dist_name = parser.get("metadata", "name", fallback=None)
    return dist_name
