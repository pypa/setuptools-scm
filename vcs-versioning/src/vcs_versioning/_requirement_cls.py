from __future__ import annotations

import logging

__all__ = ["Requirement", "extract_package_name"]

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

log = logging.getLogger(__name__)


def extract_package_name(requirement_string: str) -> str:
    """Extract the canonical package name from a requirement string.

    This function uses packaging.requirements.Requirement to properly parse
    the requirement and extract the package name, handling all edge cases
    that the custom regex-based approach might miss.

    Args:
        requirement_string: The requirement string to parse

    Returns:
        The package name as a string
    """
    return canonicalize_name(Requirement(requirement_string).name)
