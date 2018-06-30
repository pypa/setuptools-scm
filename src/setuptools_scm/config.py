""" configuration """
from __future__ import print_function, unicode_literals
import re
import warnings

from .utils import singleton

DEFAULT_TAG_REGEX = r'^(?P<prefix>\w+-)?(?P<version>v?\d+(?:\.\d+){0,2}[^\+]+)(?P<suffix>\+.*)?$'
TAG_REGEX_EXPECTED_GROUPS = set(['prefix', 'version', 'suffix'])


@singleton
class Configuration(object):
    """ Global Configuration single-instance class """

    root = ''
    version_scheme = ''
    local_scheme = ''
    write_to = ''
    write_to_template = None
    relative_to = None
    parse = None
    _tag_regex = None

    def __init__(self):
        self.root = '.'
        self.version_scheme = "guess-next-dev"
        self.local_scheme = "node-and-date"
        self.tag_regex = DEFAULT_TAG_REGEX

    @property
    def tag_regex(self):
        return self._tag_regex

    @tag_regex.setter
    def tag_regex(self, value):
        if value is None:
            value = DEFAULT_TAG_REGEX
        regex = re.compile(value)

        group_names = set(regex.groupindex.keys())
        diff = TAG_REGEX_EXPECTED_GROUPS.difference(group_names)
        if diff:
            warnings.warn("expected match groups %s missing from regex '%s'" % (diff, regex.pattern))
        diff = group_names.difference(TAG_REGEX_EXPECTED_GROUPS)
        if diff:
            warnings.warn("additional match groups %s found in regex '%s' (expected: %s)" % (diff, regex.pattern, TAG_REGEX_EXPECTED_GROUPS))

        self._tag_regex = regex
