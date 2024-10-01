# setuptools-scm

[![github ci](https://github.com/pypa/setuptools-scm/actions/workflows/python-tests.yml/badge.svg)](https://github.com/pypa/setuptools-scm/actions/workflows/python-tests.yml)
[![Documentation Status](https://readthedocs.org/projects/setuptools-scm/badge/?version=latest)](https://setuptools-scm.readthedocs.io/en/latest/?badge=latest)
[![tidelift](https://tidelift.com/badges/package/pypi/setuptools-scm) ](https://tidelift.com/subscription/pkg/pypi-setuptools-scm?utm_source=pypi-setuptools-scm&utm_medium=readme)

## about

[setuptools-scm] extracts Python package versions from `git` or `hg` metadata
instead of declaring them as the version argument
or in a Source Code Managed (SCM) managed file.

Additionally [setuptools-scm] provides `setuptools` with a list of
files that are managed by the SCM
<br/>
(i.e. it automatically adds all the SCM-managed files to the sdist).
<br/>
Unwanted files must be excluded via `MANIFEST.in`
or [configuring Git archive][git-archive-docs].

## `pyproject.toml` usage

The preferred way to configure [setuptools-scm] is to author
settings in a `tool.setuptools_scm` section of `pyproject.toml`.

This feature requires setuptools 61 or later.
First, ensure that [setuptools-scm] is present during the project's
build step by specifying it as one of the build requirements.

```toml title="pyproject.toml"
[build-system]
requires = ["setuptools>=64", "setuptools-scm>=8"]
build-backend = "setuptools.build_meta"
```

That will be sufficient to require [setuptools-scm] for projects
that support [PEP 518] like [pip] and [build].

[pip]: https://pypi.org/project/pip
[build]: https://pypi.org/project/build
[PEP 518]: https://peps.python.org/pep-0518/

To enable version inference, you need to set the version
dynamically in the `project` section of `pyproject.toml`:

```toml title="pyproject.toml"
[project]
# version = "0.0.1"  # Remove any existing version parameter.
dynamic = ["version"]

[tool.setuptools_scm]
```

Additionally, a version file can be written by specifying:

```toml title="pyproject.toml"
[tool.setuptools_scm]
version_file = "pkg/_version.py"
```

Where `pkg` is the name of your package.

If you need to confirm which version string is being generated or debug the configuration,
you can install [setuptools-scm] directly in your working environment and run:

```console
$ python -m setuptools_scm
# To explore other options, try:
$ python -m setuptools_scm --help
```

For further configuration see the [documentation].

[setuptools-scm]: https://github.com/pypa/setuptools-scm
[documentation]: https://setuptools-scm.readthedocs.io/
[git-archive-docs]: https://setuptools-scm.readthedocs.io/en/stable/usage/#builtin-mechanisms-for-obtaining-version-numbers

## Interaction with Enterprise Distributions

Some enterprise distributions like RHEL7
ship rather old setuptools versions.

In those cases its typically possible to build by using an sdist against `setuptools-scm<2.0`.
As those old setuptools versions lack sensible types for versions,
modern [setuptools-scm] is unable to support them sensibly.

It's strongly recommended to build a wheel artifact using modern Python and setuptools,
then installing the artifact instead of trying to run against old setuptools versions.

## Code of Conduct

Everyone interacting in the [setuptools-scm] project's codebases, issue
trackers, chat rooms, and mailing lists is expected to follow the
[PSF Code of Conduct].

[PSF Code of Conduct]: https://github.com/pypa/.github/blob/main/CODE_OF_CONDUCT.md

## Security Contact

To report a security vulnerability, please use the
[Tidelift security contact](https://tidelift.com/security).
Tidelift will coordinate the fix and disclosure.
