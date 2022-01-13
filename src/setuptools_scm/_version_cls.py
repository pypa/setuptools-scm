from logging import getLogger
from typing import Tuple

try:
    from packaging.version import Version, InvalidVersion

    assert hasattr(
        Version, "release"
    ), "broken installation ensure packaging>=20 is available"
except ImportError:
    from pkg_resources._vendor.packaging.version import (  # type: ignore
        Version as SetuptoolsVersion,
        InvalidVersion,
    )

    try:
        SetuptoolsVersion.release
        Version = SetuptoolsVersion  # type: ignore
    except AttributeError:

        class Version(SetuptoolsVersion):  # type: ignore
            @property
            def release(self):
                return self._version.release

            @property
            def dev(self):
                return self._version.dev

            @property
            def local(self):
                return self._version.local


class NonNormalizedVersion(Version):
    """A non-normalizing version handler.

    You can use this class to preserve version verification but skip normalization.
    For example you can use this to avoid git release candidate version tags
    ("1.0.0-rc1") to be normalized to "1.0.0rc1". Only use this if you fully
    trust the version tags.
    """

    def __init__(self, version):
        # parse and validate using parent
        super().__init__(version)

        # store raw for str
        self._raw_version = version

    def __str__(self):
        # return the non-normalized version (parent returns the normalized)
        return self._raw_version

    def __repr__(self):
        # same pattern as parent
        return f"<NonNormalizedVersion({self._raw_version!r})>"


def _version_as_tuple(version_str) -> Tuple["int | str", ...]:
    try:
        parsed_version = Version(version_str)
    except InvalidVersion:

        log = getLogger("setuptools_scm")
        log.exception("failed to parse version %s", version_str)
        return (version_str,)
    else:
        version_fields: Tuple["int | str", ...] = parsed_version.release
        if parsed_version.dev is not None:
            version_fields += (f"dev{parsed_version.dev}",)
        if parsed_version.local is not None:
            version_fields += (parsed_version.local,)
        return version_fields
