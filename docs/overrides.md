# Overrides

## pretend versions

setuptools-scm provides a mechanism to override the version number build time.

the environment variable `SETUPTOOLS_SCM_PRETEND_VERSION` is used
as the override source for the version number unparsed string.

to be specific about the package this applies for, one can use `SETUPTOOLS_SCM_PRETEND_VERSION_FOR_${NORMALIZED_DIST_NAME}`
where the dist name normalization follows adapted PEP 503 semantics.

## config overrides

setuptools-scm parses the environment variable `SETUPTOOLS_SCM_OVERRIDES_FOR_${NORMALIZED_DIST_NAME}`
as a toml inline map to override the configuration data from `pyproject.toml`.

## subprocess timeouts

The environment variable `SETUPTOOLS_SCM_SUBPROCESS_TIMEOUT` allows to override the subprocess timeout.
The default is 40 seconds and should work for most needs. However, users with git lfs + windows reported
situations where this was not enough.

