from __future__ import print_function
import datetime
import re
from .utils import trace

from pkg_resources import iter_entry_points

from distutils import log

NUMERIC_NO_LZ = r"(0|[1-9][0-9]*)"
PRE_COMPONENT = r"([a-zA-Z1-9\-][a-zA-Z0-9\-]*)"
META_COMPONENT = r"([a-zA-Z0-9\-]+)"

VERSION_RE_SRC = r"""
    ^
    v?                         # optional v prefix (as in v1.2.3)
    (?P<version>               # begin named group matching the actual version
        {NUMERIC_NO_LZ}        # major
        \.
        {NUMERIC_NO_LZ}        # minor
        (
            \.
            {NUMERIC_NO_LZ}    # optional patch
        )?
        (                      # begin optional prerelease part
            \-
            {PRE_COMPONENT}    # first component (fE "beta")
            (
                \.
                {PRE_COMPONENT}
            )*                 # and any number more
        )?                     # end prerelease
        (                      # begin optional build metadata part
            \+
            {META_COMPONENT}   # first component
            (
                \.
                {META_COMPONENT}
            )*                 # and any number more
        )?                     # end metadata
    )                          # end version
    $
""".format(
    NUMERIC_NO_LZ=NUMERIC_NO_LZ,
    PRE_COMPONENT=PRE_COMPONENT,
    META_COMPONENT=META_COMPONENT,
)

VERSION_RE = re.compile(VERSION_RE_SRC, re.VERBOSE)


try:
    from pkg_resources import parse_version, SetuptoolsVersion
except ImportError as e:
    parse_version = SetuptoolsVersion = None


def _warn_if_setuptools_outdated():
    if parse_version is None:
        log.warn("your setuptools is too old (<12)")
        log.warn("setuptools_scm functionality is degraded")


def callable_or_entrypoint(group, callable_or_name):
    trace('ep', (group, callable_or_name))
    if isinstance(callable_or_name, str):
        for ep in iter_entry_points(group, callable_or_name):
            return ep.load()
    else:
        return callable_or_name


def tag_to_version_string(tag):
    """
    Extract the version string from a tag.

    Return the longest valid SemVer at the end of the tag if it is separated
    from the rest by a hyphen (and optionally a "v" character).

    This rest is assumed to be internal information that can safely be ignored.

    Alternatively, if this is not possible, return everything after the last
    hyphen, or the entire string if no hyphen exists (old behavior).
    """

    # This implementation has two goals:
    #  - preserve, as far as possible, the old behavior of ignoring internal,
    #     non-version-relevant tag data
    #  -- assume that such data is separated from the version with a hyphen
    #  - correctly extract every SemVer version, including those containing
    #     hyphens

    # SemVer with prerelease or build metadata components can be complicated.
    # In particular, there is no good way to split the tag into internal data
    # and actual version, as there can be an arbitrary number of hyphens in
    # those components.
    # A pure regex solution would either be excessively complicated or use a
    # (slow) lazy match for the non-SemVer part of the tag.
    # Therefore, we just check progressively shorter substrings of the original
    # tag and see if they are valid SemVers.

    # For example, if our tag were tag-spam-v1.2.3-beta, we would try (in
    # order):
    #  - tag-spam-v1.2.3-beta
    #  - spam-v1.2.3-beta
    #  - v1.2.3-beta
    # The last substring would match.
    search_tag = tag
    while search_tag:
        match = VERSION_RE.match(search_tag)
        if match is not None:
            groupdict = match.groupdict()
            # version without prepended "v" if originally present
            return groupdict["version"]

        # [part_before_hyphen, part_after_hyphen] or
        # [string_without_hyphen]
        parts = search_tag.split("-", 1)

        # [part_before_hyphen, part_after_hyphen, None] or
        # [string_without_hyphen, None]
        parts.append(None)

        # part_after_hyphen or None
        search_tag = parts[1]

    # Could not find a valid SemVer, revert to using weapons from a less
    # civilized age
    return tag.rsplit('-', 1)[-1].lstrip('v')


def tag_to_version(tag):
    trace('tag', tag)
    # lstrip the v because of py2/py3 differences in setuptools
    # also required for old versions of setuptools
    version = tag_to_version_string(tag)
    if parse_version is None:
        return version
    version = parse_version(version)
    trace('version', repr(version))
    if isinstance(version, SetuptoolsVersion):
        return version


def tags_to_versions(tags):
    versions = map(tag_to_version, tags)
    return [v for v in versions if v is not None]


class ScmVersion(object):
    def __init__(self, tag_version,
                 distance=None, node=None, dirty=False,
                 **kw):
        self.tag = tag_version
        if dirty and distance is None:
            distance = 0
        self.distance = distance
        self.node = node
        self.time = datetime.datetime.now()
        self.extra = kw
        self.dirty = dirty

    @property
    def exact(self):
        return self.distance is None

    def __repr__(self):
        return self.format_with(
            '<ScmVersion {tag} d={distance}'
            ' n={node} d={dirty} x={extra}>')

    def format_with(self, fmt):
        return fmt.format(
            time=self.time,
            tag=self.tag, distance=self.distance,
            node=self.node, dirty=self.dirty, extra=self.extra)

    def format_choice(self, clean_format, dirty_format):
        return self.format_with(dirty_format if self.dirty else clean_format)


def meta(tag, distance=None, dirty=False, node=None, **kw):
    if SetuptoolsVersion is None or not isinstance(tag, SetuptoolsVersion):
        tag = tag_to_version(tag)
    trace('version', tag)

    assert tag is not None, 'cant parse version %s' % tag
    return ScmVersion(tag, distance, node, dirty, **kw)


def guess_next_version(tag_version, distance):
    version = _strip_local(str(tag_version))
    bumped = _bump_dev(version) or _bump_regex(version)
    suffix = '.dev%s' % distance
    return bumped + suffix


def _strip_local(version_string):
    public, sep, local = version_string.partition('+')
    return public


def _bump_dev(version):
    if '.dev' not in version:
        return

    prefix, tail = version.rsplit('.dev', 1)
    assert tail == '0', 'own dev numbers are unsupported'
    return prefix


def _bump_regex(version):
    prefix, tail = re.match('(.*?)(\d+)$', version).groups()
    return '%s%d' % (prefix, int(tail) + 1)


def guess_next_dev_version(version):
    if version.exact:
        return version.format_with("{tag}")
    else:
        return guess_next_version(version.tag, version.distance)


def get_local_node_and_date(version):
    if version.exact or version.node is None:
        return version.format_choice("", "+d{time:%Y%m%d}")
    else:
        return version.format_choice("+n{node}", "+n{node}.d{time:%Y%m%d}")


def get_local_dirty_tag(version):
    return version.format_choice('', '+dirty')


def postrelease_version(version):
    if version.exact:
        return version.format_with('{tag}')
    else:
        return version.format_with('{tag}.post{distance}')


def format_version(version, **config):
    trace('scm version', version)
    trace('config', config)
    version_scheme = callable_or_entrypoint(
        'setuptools_scm.version_scheme', config['version_scheme'])
    local_scheme = callable_or_entrypoint(
        'setuptools_scm.local_scheme', config['local_scheme'])
    main_version = version_scheme(version)
    trace('version', main_version)
    local_version = local_scheme(version)
    trace('local_version', local_version)
    return version_scheme(version) + local_scheme(version)
