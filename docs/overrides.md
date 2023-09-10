# Overrides

## pretend versions

setuptools_scm provides a mechanism to override the version number build time.

the environment variable `SETUPTOOLS_SCM_PRETEND_VERSION` is used
as the override source for the version number unparsed string.

to be specific about the package this applies for, one can use `SETUPTOOLS_SCM_PRETEND_VERSION_FOR_${NORMALIZED_DIST_NAME}`
where the dist name normalization follows adapted PEP 503 semantics.

## config overrides

setuptools_scm parses the environment variable `SETUPTOOLS_SCM_OVERRIDES_FOR_${NORMALIZED_DIST_NAME}`
as a toml inline map to override the configuration data from `pyproject.toml`.
