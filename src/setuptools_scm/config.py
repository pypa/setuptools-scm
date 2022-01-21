""" configuration """
import os
import re
import warnings
from typing import Type
from typing import TypeVar

from . import _types as _t
from ._version_cls import NonNormalizedVersion
from ._version_cls import Version
from .utils import trace

DEFAULT_TAG_REGEX = r"^(?:[\w-]+-)?(?P<version>[vV]?\d+(?:\.\d+){0,2}[^\+]*)(?:\+.*)?$"
DEFAULT_VERSION_SCHEME = "guess-next-dev"
DEFAULT_LOCAL_SCHEME = "node-and-date"


def _check_tag_regex(value):
    if not value:
        value = DEFAULT_TAG_REGEX
    regex = re.compile(value)

    group_names = regex.groupindex.keys()
    if regex.groups == 0 or (regex.groups > 1 and "version" not in group_names):
        warnings.warn(
            "Expected tag_regex to contain a single match group or a group named"
            " 'version' to identify the version part of any tag."
        )

    return regex


def _check_absolute_root(root: _t.PathT, relative_to: _t.PathT):
    trace("abs root", repr(locals()))
    if relative_to:
        if (
            os.path.isabs(root)
            and not os.path.commonpath([root, relative_to]) == relative_to
        ):
            warnings.warn(
                "absolute root path '%s' overrides relative_to '%s'"
                % (root, relative_to)
            )
        if os.path.isdir(relative_to):
            warnings.warn(
                "relative_to is expected to be a file,"
                " its the directory %r\n"
                "assuming the parent directory was passed" % (relative_to,)
            )
            trace("dir", relative_to)
            root = os.path.join(relative_to, root)
        else:
            trace("file", relative_to)
            root = os.path.join(os.path.dirname(relative_to), root)
    return os.path.abspath(root)


def _lazy_tomli_load(data: str):
    from tomli import loads

    return loads(data)


VersionT = TypeVar("VersionT", Version, NonNormalizedVersion)


class Configuration:
    """Global configuration model"""

    _root: _t.PathT
    _relative_to: "_t.PathT | None"
    version_cls: "Type[Version]|Type[NonNormalizedVersion]"

    def __init__(
        self,
        relative_to: "_t.PathT | None" = None,
        root: _t.PathT = ".",
        version_scheme: str = DEFAULT_VERSION_SCHEME,
        local_scheme=DEFAULT_LOCAL_SCHEME,
        write_to: "_t.PathT | None" = None,
        write_to_template: "str|None" = None,
        tag_regex=DEFAULT_TAG_REGEX,
        parentdir_prefix_version=None,
        fallback_version: "str|None" = None,
        fallback_root: _t.PathT = ".",
        parse=None,
        git_describe_command=None,
        dist_name: str = None,
        version_cls: "Type[Version]|Type[NonNormalizedVersion]|str|None" = None,
        normalize: bool = True,
        search_parent_directories: bool = False,
    ):
        # TODO:
        self._relative_to = relative_to
        self._root = "."

        self.root = root
        self.version_scheme = version_scheme
        self.local_scheme = local_scheme
        self.write_to = write_to
        self.write_to_template = write_to_template
        self.parentdir_prefix_version = parentdir_prefix_version
        self.fallback_version = fallback_version
        self.fallback_root = fallback_root
        self.parse = parse
        self.tag_regex = tag_regex
        self.git_describe_command = git_describe_command
        self.dist_name = dist_name
        self.search_parent_directories = search_parent_directories
        self.parent = None

        if not normalize:
            # `normalize = False` means `version_cls = NonNormalizedVersion`
            if version_cls is not None:
                raise ValueError(
                    "Providing a custom `version_cls` is not permitted when "
                    "`normalize=False`"
                )
            self.version_cls = NonNormalizedVersion
        else:
            # Use `version_cls` if provided, default to packaging or pkg_resources
            if version_cls is None:
                self.version_cls = Version
            elif isinstance(version_cls, str):
                try:
                    # Not sure this will work in old python
                    import importlib

                    pkg, cls_name = version_cls.rsplit(".", 1)
                    version_cls_host = importlib.import_module(pkg)
                    self.version_cls = getattr(version_cls_host, cls_name)
                except:  # noqa
                    raise ValueError(f"Unable to import version_cls='{version_cls}'")
            else:
                self.version_cls = version_cls

    @property
    def fallback_root(self):
        return self._fallback_root

    @fallback_root.setter
    def fallback_root(self, value):
        self._fallback_root = os.path.abspath(value)

    @property
    def absolute_root(self):
        return self._absolute_root

    @property
    def relative_to(self):
        return self._relative_to

    @relative_to.setter
    def relative_to(self, value):
        self._absolute_root = _check_absolute_root(self._root, value)
        self._relative_to = value
        trace("root", repr(self._absolute_root))
        trace("relative_to", repr(value))

    @property
    def root(self):
        return self._root

    @root.setter
    def root(self, value):
        self._absolute_root = _check_absolute_root(value, self._relative_to)
        self._root = value
        trace("root", repr(self._absolute_root))
        trace("relative_to", repr(self._relative_to))

    @property
    def tag_regex(self):
        return self._tag_regex

    @tag_regex.setter
    def tag_regex(self, value):
        self._tag_regex = _check_tag_regex(value)

    @classmethod
    def from_file(
        cls,
        name: str = "pyproject.toml",
        dist_name=None,  # type: str | None
        _load_toml=_lazy_tomli_load,
        **kwargs,
    ):
        """
        Read Configuration from pyproject.toml (or similar).
        Raises exceptions when file is not found or toml is
        not installed or the file has invalid format or does
        not contain the [tool.setuptools_scm] section.
        """

        with open(name, encoding="UTF-8") as strm:
            data = strm.read()
        defn = _load_toml(data)
        try:
            section = defn.get("tool", {})["setuptools_scm"]
        except LookupError as e:
            raise LookupError(
                f"{name} does not contain a tool.setuptools_scm section"
            ) from e
        if "dist_name" in section:
            if dist_name is None:
                dist_name = section.pop("dist_name")
            else:
                assert dist_name == section["dist_name"]
                del section["dist_name"]
        if dist_name is None:
            if "project" in defn:
                # minimal pep 621 support for figuring the pretend keys
                dist_name = defn["project"].get("name")
        if dist_name is None:
            dist_name = _read_dist_name_from_setup_cfg()

        return cls(dist_name=dist_name, **section, **kwargs)


def _read_dist_name_from_setup_cfg():

    # minimal effort to read dist_name off setup.cfg metadata
    import configparser

    parser = configparser.ConfigParser()
    parser.read(["setup.cfg"])
    dist_name = parser.get("metadata", "name", fallback=None)
    return dist_name
