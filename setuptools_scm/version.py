import re
import datetime
from .utils import trace

# extended pep 386 regex
# see http://www.python.org/dev/peps/pep-0386/#the-new-versioning-algorithm
version_re = r"""^
(?P<prefix>\w+-?)?         # any text, may have a dash
                              # custom to deal with tag prefixes
(?P<version>\d+\.\d+)         # minimum 'N.N'
(?P<extraversion>(?:\.\d+)*)  # any number of extra '.N' segments
(?P<prerelfullversion>
(:?
    (?P<prerel>[abc]|rc)         # 'a' = alpha, 'b' = beta
                                 # 'c' or 'rc' = release candidate
    (?P<prerelversion>\d+(?:\.\d+)*)
)?)
# we dont mach those, its our job to generate dontev markers
# we match those and dev should have nothing that follow
(?P<postdev>
    (\.post(?P<post>\d+))?
    (\.dev(?P<dev>\d+)?)?
)?
$"""


def tag_to_version(tag):
    trace(tag)
    match = re.match(version_re, tag, re.VERBOSE)
    if match is not None:
        return ''.join(match.group(
            'version', 'extraversion', 'prerelfullversion', 'postdev'
        ))


def tags_to_versions(tags):
    versions = map(tag_to_version, tags)
    return list(filter(None, versions))


def meta(tag, distance=None, node=None, dirty=False, **kw):
    version = tag_to_version(tag)
    trace('version', version)
    assert version is not None, 'cant parse version %s' % tag
    if (version.endswith('.dev') and distance is None):
        distance = 0
    time = datetime.date.today().strftime('%Y%m%d')
    return dict(
        tag=version,
        distance=distance,
        node=node,
        dirty=dirty,
        time=time,
        **kw
    )
