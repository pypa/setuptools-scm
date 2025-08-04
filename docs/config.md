# Configuration

## When is configuration needed?

Starting with setuptools-scm 8.1+, explicit configuration is **optional** in many cases:

- **No configuration needed**: If `setuptools_scm` (or `setuptools-scm`) is in your `build-system.requires`, setuptools-scm will automatically activate with sensible defaults.

- **Configuration recommended**: Use the `[tool.setuptools_scm]` section when you need to:
  - Write version files (`version_file`)
  - Customize version schemes (`version_scheme`, `local_scheme`)
  - Set custom tag patterns (`tag_regex`)
  - Configure fallback behavior (`fallback_version`)
  - Or any other non-default behavior

## configuration parameters

Configuration parameters can be configured in `pyproject.toml` or `setup.py`.
Callables or other Python objects have to be passed in `setup.py` (via the `use_scm_version` keyword argument).


`root : Path | PathLike[str]`
: Relative path to the SCM root, defaults to `.` and is relative to the file path passed in `relative_to`

`version_scheme : str | Callable[[ScmVersion], str]`
: Configures how the version number is constructed; either an entrypoint name or a callable.
  See [Version number construction](extending.md#setuptools_scmversion_scheme) for predefined implementations.

`local_scheme : str | Callable[[ScmVersion], str]`
: Configures how the local component of the version (the optional part after the `+`) is constructed;
  either an entrypoint name or a callable.
  See [Version number construction](extending.md#setuptools_scmlocal_scheme) for predefined implementations.


`version_file: Path | PathLike[str] | None = None`
:   A path to a file that gets replaced with a file containing the current
    version. It is ideal for creating a ``_version.py`` file within the
    package, typically used to avoid using `importlib.metadata`
    (which adds some overhead).

    !!! warning ""

        Only files with `.py` and `.txt` extensions have builtin templates,
        for other file types it is necessary to provide `version_file_template`.

`version_file_template: str | None = None`
:   A new-style format string taking `version`, `scm_version` and `version_tuple` as parameters.
    `version` is the generated next_version as string,
    `version_tuple` is a tuple of split numbers/strings and
    `scm_version` is the `ScmVersion` instance the current `version` was rendered from


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
    which supports tags with optional "v" prefix (recommended), project prefixes,
    and various version formats.

    !!! tip

        The default regex supports common tag formats like `v1.0.0`, `myproject-v1.0.0`,
        and `1.0.0`. For best practices on tag naming, see
        [Version Tag Formats](usage.md#version-tag-formats).

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
    unset (the default), `setuptools-scm` will error if it fails to detect the
    version.

`fallback_root: Path | PathLike[str] = "."`
:   The directory to use when SCM metadata is not available (e.g., in extracted
    archives like PyPI tarballs). This is particularly useful for legacy
    configurations that need to work both in development (with SCM metadata)
    and from archives (without SCM metadata). Defaults to the current directory.

    When SCM metadata is present, the `root` parameter is used; when it's not
    available, `fallback_root` is used instead. This allows the same configuration
    to work in both scenarios without modification.

`parse: Callable[[Path, Config], ScmVersion] | None = None`
:   A function that will be used instead of the discovered SCM
    for parsing the version. Use with caution,
    this is a function for advanced use and you should be
    familiar with the `setuptools-scm` internals to use it.

`scm.git.describe_command`
:   This command will be used instead the default `git describe --long` command.

    Defaults to the value set by [setuptools_scm.git.DEFAULT_DESCRIBE][]

`scm.git.pre_parse`
:   A string specifying which git pre-parse function to use before parsing version information.
    Available options:

    - `"warn_on_shallow"` (default): Warns when the repository is shallow
    - `"fail_on_shallow"`: Fails with an error when the repository is shallow
    - `"fetch_on_shallow"`: Automatically fetches to rectify shallow repositories
    - `"fail_on_missing_submodules"`: Fails when submodules are defined but not initialized

        The `"fail_on_missing_submodules"` option is useful to prevent packaging incomplete
    projects when submodules are required for a complete build.

    Note: This setting is overridden by any explicit `pre_parse` parameter passed to the git parse function.

`git_describe_command` (deprecated)
:   **Deprecated since 8.4.0**: Use `scm.git.describe_command` instead.

    This field is maintained for backward compatibility but will issue a deprecation warning when used.

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
    `packaging.version.Version`. If this is used while `setuptools-scm`
    is integrated in a setuptools packaging process, the non-normalized
    version number will appear in all files (see `version_file` note).

    !!! note "normalization still applies to artifact filenames"
        Setuptools will still normalize it to create the final distribution,
        so as to stay compliant with the python packaging standards.


## environment variables

`SETUPTOOLS_SCM_PRETEND_VERSION`
:   used as the primary source for the version number
    in which case it will be an unparsed string

    !!! warning ""

        it is strongly recommended to use distribution-specific pretend versions
        (see below).

`SETUPTOOLS_SCM_PRETEND_VERSION_FOR_${DIST_NAME}`
:   used as the primary source for the version number,
    in which case it will be an unparsed string.
    Specifying distribution-specific pretend versions will
    avoid possible collisions with third party distributions
    also using ``setuptools-scm``

    the dist name normalization follows adapted PEP 503 semantics, with one or
    more of ".-\_" being replaced by a single "\_", and the name being upper-cased

    this will take precedence over ``SETUPTOOLS_SCM_PRETEND_VERSION``

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

`SETUPTOOLS_SCM_HG_COMMAND`
:   command used for running Mercurial (defaults to ``hg``)

    for example, set this to ``chg`` to reduce start-up overhead of Mercurial





## automatic file inclusion

!!! warning "Setuptools File Finder Integration"

    `setuptools-scm` automatically registers a setuptools file finder that includes all SCM-tracked files in source distributions. This behavior is **always active** when setuptools-scm is installed, regardless of whether you use it for versioning.

**How it works:**

`setuptools-scm` provides a `setuptools.file_finders` entry point that:

1. Automatically discovers SCM-managed files (Git, Mercurial)
2. Includes them in source distributions (`python -m build --sdist`)
3. Works for `include_package_data = True` in package building

**Entry point registration:**
```toml
[project.entry-points."setuptools.file_finders"]
setuptools_scm = "setuptools_scm._file_finders:find_files"
```

**Files included by default:**
- All files tracked by Git (`git ls-files`)
- All files tracked by Mercurial (`hg files`)
- Includes: source code, documentation, tests, config files, etc.
- Excludes: untracked files, files in `.gitignore`/`.hgignore`

**Controlling inclusion:**

Use `MANIFEST.in` to override the automatic behavior:

```text title="MANIFEST.in"
# Exclude development files
exclude .pre-commit-config.yaml
exclude tox.ini
global-exclude *.pyc __pycache__/

# Exclude entire directories
prune docs/
prune testing/

# Include non-SCM files
include data/important.json
```

**Debugging file inclusion:**

```bash
# List files that will be included
python -m setuptools_scm ls

# Build and inspect sdist contents
python -m build --sdist
tar -tzf dist/package-*.tar.gz
```

!!! note "Cannot be disabled"

    The file finder cannot be disabled through configuration - it's automatically active when setuptools-scm is installed. If you need to disable it completely, you must remove setuptools-scm from your build environment (which also means you can't use it for versioning).


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
