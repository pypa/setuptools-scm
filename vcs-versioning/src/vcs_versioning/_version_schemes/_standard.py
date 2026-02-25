"""Standard version and local schemes for setuptools-scm.

This module contains the built-in version schemes and local schemes that determine
how version numbers are calculated and formatted.
"""

from __future__ import annotations

import logging
import re
import warnings
from datetime import date, datetime, timedelta, timezone
from re import Match
from typing import TYPE_CHECKING

from .. import _modify_version
from .._scm_version import ScmVersion, _parse_version_tag
from .._version_cls import Version as PkgVersion
from ._common import SEMVER_LEN, SEMVER_MINOR, SEMVER_PATCH

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)


# Version Schemes
# ----------------


def guess_next_version(tag_version: ScmVersion) -> str:
    version = _modify_version.strip_local(str(tag_version.tag))
    return _modify_version._bump_dev(version) or _modify_version._bump_regex(version)


def guess_next_dev_version(version: ScmVersion) -> str:
    if version.exact:
        return version.format_with("{tag}")
    else:
        return version.format_next_version(guess_next_version)


def guess_next_simple_semver(
    version: ScmVersion, retain: int, increment: bool = True
) -> str:
    parts = list(version.tag.release[:retain])
    while len(parts) < retain:
        parts.append(0)
    if increment:
        parts[-1] += 1
    while len(parts) < SEMVER_LEN:
        parts.append(0)
    return ".".join(str(i) for i in parts)


def simplified_semver_version(version: ScmVersion) -> str:
    if version.exact:
        return guess_next_simple_semver(version, retain=SEMVER_LEN, increment=False)
    elif version.branch is not None and "feature" in version.branch:
        return version.format_next_version(
            guess_next_simple_semver, retain=SEMVER_MINOR
        )
    else:
        return version.format_next_version(
            guess_next_simple_semver, retain=SEMVER_PATCH
        )


def release_branch_semver_version(version: ScmVersion) -> str:
    if version.exact:
        return version.format_with("{tag}")
    if version.branch is not None:
        # Does the branch name (stripped of namespace) parse as a version?
        branch_ver_data = _parse_version_tag(
            version.branch.split("/")[-1], version.config
        )
        if branch_ver_data is not None:
            branch_ver = branch_ver_data["version"]
            if branch_ver[0] == "v":
                # Allow branches that start with 'v', similar to Version.
                branch_ver = branch_ver[1:]
            # Does the branch version up to the minor part match the tag? If not it
            # might be like, an issue number or something and not a version number, so
            # we only want to use it if it matches.
            tag_ver_up_to_minor = str(version.tag).split(".")[:SEMVER_MINOR]
            branch_ver_up_to_minor = branch_ver.split(".")[:SEMVER_MINOR]
            if branch_ver_up_to_minor == tag_ver_up_to_minor:
                # We're in a release/maintenance branch, next is a patch/rc/beta bump:
                return version.format_next_version(guess_next_version)
    # We're in a development branch, next is a minor bump:
    return version.format_next_version(guess_next_simple_semver, retain=SEMVER_MINOR)


def _deprecated_simplified_semver_version(version: ScmVersion) -> str:
    warnings.warn(
        "Version scheme 'python-simplified-semver' has been renamed to 'semver-pep440'. "
        "Please update your configuration. "
        "The old name will be removed in a future version.",
        DeprecationWarning,
        stacklevel=2,
    )
    return simplified_semver_version(version)


def _deprecated_release_branch_semver_version(version: ScmVersion) -> str:
    warnings.warn(
        "Version scheme 'release-branch-semver' has been renamed to "
        "'semver-pep440-release-branch'. "
        "Please update your configuration. "
        "The old name will be removed in a future version.",
        DeprecationWarning,
        stacklevel=2,
    )
    return release_branch_semver_version(version)


def release_branch_semver(version: ScmVersion) -> str:
    warnings.warn(
        "release_branch_semver is deprecated and will be removed in the future. "
        "Use release_branch_semver_version instead",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return release_branch_semver_version(version)


def only_version(version: ScmVersion) -> str:
    return version.format_with("{tag}")


def no_guess_dev_version(version: ScmVersion) -> str:
    if version.exact:
        return version.format_with("{tag}")
    else:
        return version.format_next_version(_modify_version._dont_guess_next_version)


_DATE_REGEX = re.compile(
    r"""
    ^(?P<date>
        (?P<prefix>[vV]?)
        (?P<year>\d{2}|\d{4})(?:\.\d{1,2}){2})
        (?:\.(?P<patch>\d*))?$
    """,
    re.VERBOSE,
)


def date_ver_match(ver: str) -> Match[str] | None:
    return _DATE_REGEX.match(ver)


def guess_next_date_ver(
    version: ScmVersion,
    node_date: date | None = None,
    date_fmt: str | None = None,
    version_cls: type | None = None,
) -> str:
    """
    same-day -> patch +1
    other-day -> today

    distance is always added as .devX
    """
    match = date_ver_match(str(version.tag))
    if match is None:
        warnings.warn(
            f"{version} does not correspond to a valid versioning date, "
            "assuming legacy version",
            stacklevel=2,
        )
        if date_fmt is None:
            date_fmt = "%y.%m.%d"
    else:
        # deduct date format if not provided
        if date_fmt is None:
            date_fmt = "%Y.%m.%d" if len(match.group("year")) == 4 else "%y.%m.%d"
        if prefix := match.group("prefix"):
            if not date_fmt.startswith(prefix):
                date_fmt = prefix + date_fmt

    today = version.time.date()
    head_date = node_date or today
    # compute patch
    if match is None:
        # For legacy non-date tags, always use patch=0 (treat as "other day")
        # Use yesterday to ensure tag_date != head_date
        tag_date = head_date - timedelta(days=1)
    else:
        tag_date = (
            datetime.strptime(match.group("date"), date_fmt)
            .replace(tzinfo=timezone.utc)
            .date()
        )
    if tag_date == head_date:
        assert match is not None
        # Same day as existing date tag - increment patch
        patch = int(match.group("patch") or "0") + 1
    else:
        # Different day or legacy non-date tag - use patch 0
        if tag_date > head_date and match is not None:
            # warn on future times (only for actual date tags, not legacy)
            warnings.warn(
                f"your previous tag  ({tag_date}) is ahead your node date ({head_date})",
                stacklevel=2,
            )
        patch = 0
    next_version = "{node_date:{date_fmt}}.{patch}".format(
        node_date=head_date, date_fmt=date_fmt, patch=patch
    )
    # rely on the Version object to ensure consistency (e.g. remove leading 0s)
    if version_cls is None:
        version_cls = PkgVersion
    next_version = str(version_cls(next_version))
    return next_version


def calver_by_date(version: ScmVersion) -> str:
    if version.exact and not version.dirty:
        return version.format_with("{tag}")
    # TODO: move the release-X check to a new scheme
    if version.branch is not None and version.branch.startswith("release-"):
        branch_ver = _parse_version_tag(version.branch.split("-")[-1], version.config)
        if branch_ver is not None:
            ver = branch_ver["version"]
            match = date_ver_match(ver)
            if match:
                return ver
    return version.format_next_version(
        guess_next_date_ver,
        node_date=version.node_date,
        version_cls=version.config.version_cls,
    )


def postrelease_version(version: ScmVersion) -> str:
    if version.exact:
        return version.format_with("{tag}")
    else:
        return version.format_with("{tag}.post{distance}")


# Local Schemes
# -------------


def get_local_node_and_date(version: ScmVersion) -> str:
    return _modify_version._format_local_with_time(version, time_format="%Y%m%d")


def get_local_node_and_timestamp(version: ScmVersion) -> str:
    return _modify_version._format_local_with_time(version, time_format="%Y%m%d%H%M%S")


def get_local_dirty_tag(version: ScmVersion) -> str:
    return version.format_choice("", "+dirty")


def get_no_local_node(version: ScmVersion) -> str:
    return ""
