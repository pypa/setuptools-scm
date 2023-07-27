# Configuration


## configuration parameters

## environment variables

`SETUPTOOLS_SCM_PRETEND_VERSION`
:   its used as the primary source for the version number
    in which case it will be an unparsed string

    !!! warning "its strongly  recommended to use use distribution name specific pretend versions"


`SETUPTOOLS_SCM_PRETEND_VERSION_FOR_${NORMALIZED_DIST_NAME}`
:   its used as the primary source for the version number
    in which case it will be an unparsed string

    the dist name normalization follows adapted PEP-503 semantics, with one or
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
::: setuptools_scm.Configuration
