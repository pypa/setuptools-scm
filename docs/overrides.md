# Overrides

## pretend versions

setuptools-scm provides a mechanism to override the version number build time.

the environment variable `SETUPTOOLS_SCM_PRETEND_VERSION` is used
as the override source for the version number unparsed string.

to be specific about the package this applies for, one can use `SETUPTOOLS_SCM_PRETEND_VERSION_FOR_${DIST_NAME}`
where the dist name normalization follows adapted PEP 503 semantics.

## pretend metadata

setuptools-scm provides a mechanism to override individual version metadata fields at build time.

The environment variable `SETUPTOOLS_SCM_PRETEND_METADATA` accepts a TOML inline table
with field overrides for the ScmVersion object.

To be specific about the package this applies for, one can use `SETUPTOOLS_SCM_PRETEND_METADATA_FOR_${DIST_NAME}`
where the dist name normalization follows adapted PEP 503 semantics.

### Supported fields

The following ScmVersion fields can be overridden:

- `distance` (int): Number of commits since the tag
- `node` (str): The commit hash/node identifier
- `dirty` (bool): Whether the working directory has uncommitted changes
- `branch` (str): The branch name
- `node_date` (date): The date of the commit (TOML date format: `2024-01-15`)
- `time` (datetime): The version timestamp (TOML datetime format)
- `preformatted` (bool): Whether the version string is preformatted
- `tag`: The version tag (can be string or version object)

### Examples

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

### Use case: CI/CD environments

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

## config overrides

setuptools-scm parses the environment variable `SETUPTOOLS_SCM_OVERRIDES_FOR_${DIST_NAME}`
as a toml inline map to override the configuration data from `pyproject.toml`.

## subprocess timeouts

The environment variable `SETUPTOOLS_SCM_SUBPROCESS_TIMEOUT` allows to override the subprocess timeout.
The default is 40 seconds and should work for most needs. However, users with git lfs + windows reported
situations where this was not enough.

