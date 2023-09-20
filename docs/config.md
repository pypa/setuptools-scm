# Configuration


## configuration parameters

Configuration parameters can be configured in `pyproject.toml` or `setup.py`.
Callables or other Python objects have to be passed in `setup.py` (via the `use_scm_version` keyword argument).


`root : Path | PathLike[str]`
: Relative path to the SCM root, defaults to `.` and is relative to the file path passed in `relative_to`

`version_scheme : str | Callable[[ScmVersion], str]`
: Configures how the local version number is constructed; either an entrypoint name or a callable.

`local_scheme : str | Callable[[ScmVersion], str]`
: Configures how the local component of the version is constructed
  either an entrypoint name or a callable.


`version_file: Path | PathLike[str] | None = None`
:   A path to a file that gets replaced with a file containing the current
    version. It is ideal for creating a ``_version.py`` file within the
    package, typically used to avoid using `pkg_resources.get_distribution`
    (which adds some overhead).

    !!! warning ""

        Only files with `.py` and `.txt` extensions have builtin templates,
        for other file types it is necessary to provide `write_to_template`.

`version_file_template_template: str | None = None`
:   A new-style format string that is given the current version as
    the `version` keyword argument for formatting.

`write_to: Pathlike[str] | Path | None = None`
:  (deprecated) legacy option to create a version file relative to the scm root
   it's broken for usage from a sdist and fixing it would be a fatal breaking change,
   use `version_file` instead.

`relative_to: Path|Pathlike[str] = "pyproject.toml"`
:   A file/directory from which the root can be resolved.
    Typically called by a script or module that is not in the root of the
    repository to point `setuptools_scm` at the root of the repository by
    supplying `__file__`.

`tag_regex: str|Pattern[str]`
:   A Python regex string to extract the version part from any SCM tag.
    The regex needs to contain either a single match group, or a group
    named `version`, that captures the actual version information.

    Defaults to the value of [setuptools_scm._config.DEFAULT_TAG_REGEX][]

`parentdir_prefix_version: str|None = None`
:   If the normal methods for detecting the version (SCM version,
    sdist metadata) fail, and the parent directory name starts with
    `parentdir_prefix_version`, then this prefix is stripped and the rest of
    the parent directory name is matched with `tag_regex` to get a version
    string.  If this parameter is unset (the default), then this fallback is
    not used.

    This was intended to cover GitHub's "release tarballs",
    which extract into directories named `projectname-tag/`
    (in which case `parentdir_prefix_version` can be set e.g. to `projectname-`).

`fallback_version: str | None = None`
 :  A version string that will be used if no other method for detecting the
    version worked (e.g., when using a tarball with no metadata). If this is
    unset (the default), `setuptools_scm` will error if it fails to detect the
    version.

`parse: Callable[[Path, Config], ScmVersion] | None = None`
:   A function that will be used instead of the discovered SCM
    for parsing the version. Use with caution,
    this is a function for advanced use and you should be
    familiar with the `setuptools_scm` internals to use it.

`git_describe_command`
:   This command will be used instead the default `git describe --long` command.

    Defaults to the value set by [setuptools_scm.git.DEFAULT_DESCRIBE][]

`normalize`
:   A boolean flag indicating if the version string should be normalized.
    Defaults to `True`. Setting this to `False` is equivalent to setting
    `version_cls` to [setuptools_scm.NonNormalizedVersion][]

`version_cls: type|str = packaging.version.Version`
:   An optional class used to parse, verify and possibly normalize the version
    string. Its constructor should receive a single string argument, and its
    `str` should return the normalized version string to use.
    This option can also receive a class qualified name as a string.

    The [setuptools_scm.NonNormalizedVersion][] convenience class is
    provided to disable the normalization step done by
    `packaging.version.Version`. If this is used while `setuptools_scm`
    is integrated in a setuptools packaging process, the non-normalized
    version number will appear in all files (see `version_file` note).

    !!! note "normalization still applies to artifact filenames"
        Setuptools will still normalize it to create the final distribution,
        so as to stay compliant with the python packaging standards.


## environment variables

`SETUPTOOLS_SCM_PRETEND_VERSION`
:   used as the primary source for the version number
    in which case it will be an unparsed string

    !!! warning "it is strongly recommended to use use distribution name specific pretend versions"


`SETUPTOOLS_SCM_PRETEND_VERSION_FOR_${NORMALIZED_DIST_NAME}`
:   used as the primary source for the version number
    in which case it will be an unparsed string

    the dist name normalization follows adapted PEP 503 semantics, with one or
    more of ".-_" being replaced by a single "_", and the name being upper-cased

    it takes precedence over ``SETUPTOOLS_SCM_PRETEND_VERSION``

`SETUPTOOLS_SCM_DEBUG`
:    enable the debug logging

`SOURCE_DATE_EPOCH`
:   used as the timestamp from which the
    ``node-and-date`` and ``node-and-timestamp`` local parts are
    derived, otherwise the current time is used
    (https://reproducible-builds.org/docs/source-date-epoch/)

`SETUPTOOLS_SCM_IGNORE_VCS_ROOTS`
:   a ``os.pathsep`` separated list
    of directory names to ignore for root finding





## api reference

### constants

::: setuptools_scm._config.DEFAULT_TAG_REGEX
    options:
      heading_level: 4

::: setuptools_scm.git.DEFAULT_DESCRIBE
    options:
      heading_level: 4


### the configuration class
::: setuptools_scm.Configuration
    options:
      heading_level: 4
