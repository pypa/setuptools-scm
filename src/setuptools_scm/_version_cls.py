try:
    from packaging.version import Version

    assert hasattr(Version, "release")
except ImportError:
    from pkg_resources._vendor.packaging.version import Version as SetuptoolsVersion

    try:
        SetuptoolsVersion.release
        Version = SetuptoolsVersion
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
