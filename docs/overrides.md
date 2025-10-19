# Overrides

## About Overrides

Environment variables provide runtime configuration overrides, primarily useful in CI/CD
environments where you need different behavior without modifying `pyproject.toml` or code.

## Version Detection Overrides

### Pretend Versions

Override the version number at build time.

**setuptools-scm usage:**

The environment variable `SETUPTOOLS_SCM_PRETEND_VERSION` is used
as the override source for the version number unparsed string.

!!! warning ""

    it is strongly recommended to use distribution-specific pretend versions
    (see below).

`SETUPTOOLS_SCM_PRETEND_VERSION_FOR_${DIST_NAME}`
:   Used as the primary source for the version number,
    in which case it will be an unparsed string.
    Specifying distribution-specific pretend versions will
    avoid possible collisions with third party distributions
    also using vcs-versioning.

    The dist name normalization follows adapted PEP 503 semantics, with one or
    more of ".-\_" being replaced by a single "\_", and the name being upper-cased.

    This will take precedence over ``SETUPTOOLS_SCM_PRETEND_VERSION``.

### Pretend Metadata

Override individual version metadata fields at build time.

**setuptools-scm usage:**

`SETUPTOOLS_SCM_PRETEND_METADATA`
:   Accepts a TOML inline table with field overrides for the ScmVersion object.

`SETUPTOOLS_SCM_PRETEND_METADATA_FOR_${DIST_NAME}`
:   Same as above but specific to a package (recommended over the generic version).
    The dist name normalization follows adapted PEP 503 semantics.

#### Supported fields

The following ScmVersion fields can be overridden:

- `distance` (int): Number of commits since the tag
- `node` (str): The commit hash/node identifier
- `dirty` (bool): Whether the working directory has uncommitted changes
- `branch` (str): The branch name
- `node_date` (date): The date of the commit (TOML date format: `2024-01-15`)
- `time` (datetime): The version timestamp (TOML datetime format)
- `preformatted` (bool): Whether the version string is preformatted
- `tag`: The version tag (can be string or version object)

#### Examples

Override commit hash and distance:
```bash
export SETUPTOOLS_SCM_PRETEND_METADATA='{node="g1337beef", distance=4}'
```

Override multiple fields with proper TOML types:
```bash
export SETUPTOOLS_SCM_PRETEND_METADATA='{node="gabcdef12", distance=7, dirty=true, node_date=2024-01-15}'
```

Use with a specific package:
```bash
export SETUPTOOLS_SCM_PRETEND_METADATA_FOR_MY_PACKAGE='{node="g1234567", distance=2}'
```

!!! note "Node ID Prefixes"

    Node IDs must include the appropriate SCM prefix:

    - Use `g` prefix for git repositories (e.g., `g1a2b3c4d5`)
    - Use `h` prefix for mercurial repositories (e.g., `h1a2b3c4d5`)

    This ensures consistency with setuptools-scm's automatic node ID formatting.

#### Use case: CI/CD environments

This is particularly useful for solving issues where version file templates need access to
commit metadata that may not be available in certain build environments:

```toml
[tool.setuptools_scm]
version_file = "src/mypackage/_version.py"
version_file_template = '''
version = "{version}"
commit_hash = "{scm_version.node}"
commit_count = {scm_version.distance}
'''
```

With pretend metadata, you can ensure the template gets the correct values:
```bash
export SETUPTOOLS_SCM_PRETEND_VERSION="1.2.3.dev4+g1337beef"
export SETUPTOOLS_SCM_PRETEND_METADATA='{node="g1337beef", distance=4}'
```

### Debug Logging

Enable debug output from vcs-versioning.

**setuptools-scm usage:**

`SETUPTOOLS_SCM_DEBUG`
:   Enable debug logging for version detection and processing.

### Reproducible Builds

Control timestamps for reproducible builds (from [reproducible-builds.org](https://reproducible-builds.org/docs/source-date-epoch/)).

`SOURCE_DATE_EPOCH`
:   Used as the timestamp from which the ``node-and-date`` and ``node-and-timestamp``
    local parts are derived, otherwise the current time is used.
    This is a standard environment variable supported by many build tools.

## setuptools-scm Overrides

### Configuration Overrides

`SETUPTOOLS_SCM_OVERRIDES_FOR_${DIST_NAME}`
:   A TOML inline table to override configuration from `pyproject.toml`.
    This allows overriding any configuration option at build time, which is particularly useful
    in CI/CD environments where you might want different behavior without modifying `pyproject.toml`.

    **Example:**
    ```bash
    # Override local_scheme for CI builds
    export SETUPTOOLS_SCM_OVERRIDES_FOR_MYPACKAGE='{"local_scheme": "no-local-version"}'
    ```

### SCM Root Discovery

`SETUPTOOLS_SCM_IGNORE_VCS_ROOTS`
:   A ``os.pathsep`` separated list of directory names to ignore for root finding.

### Mercurial Command

`SETUPTOOLS_SCM_HG_COMMAND`
:   Command used for running Mercurial (defaults to ``hg``).
    For example, set this to ``chg`` to reduce start-up overhead of Mercurial.

### Subprocess Timeouts

`SETUPTOOLS_SCM_SUBPROCESS_TIMEOUT`
:   Override the subprocess timeout (default: 40 seconds).
    The default should work for most needs. However, users with git lfs + windows reported
    situations where this was not enough.

    **Example:**
    ```bash
    # Increase timeout to 120 seconds
    export SETUPTOOLS_SCM_SUBPROCESS_TIMEOUT=120
    ```

