# About

`setuptools-scm` extracts Python package versions from `git` or `hg` metadata
instead of declaring them as the version argument
or in a Source Code Managed (SCM) managed file.

Additionally `setuptools-scm` provides `setuptools` with a list of
files that are managed by the SCM
(i.e. it automatically adds all the SCM-managed files to the sdist).
Unwanted files must be excluded via `MANIFEST.in`
or [configuring Git archive][git-archive-docs].

[git-archive-docs]: usage.md#builtin-mechanisms-for-obtaining-version-numbers

## Basic usage

### With setuptools

Note: `setuptools-scm>=8` intentionally doesn't depend on setuptools to ease non-setuptools usage.
Please ensure a recent version of setuptools (>=64) is installed.


```toml title="pyproject.toml"
[build-system]
requires = ["setuptools>=64", "setuptools-scm>=8"]
build-backend = "setuptools.build_meta"

[project]
name = "example"
# Important: Remove any existing version declaration
# version = "0.0.1"
dynamic = ["version"]
# more missing

[tool.setuptools_scm]

```


### With hatch

[Hatch-vcs](https://github.com/ofek/hatch-vcs) integrates with setuptools-scm
but provides its own configuration options,
please see its [documentation](https://github.com/ofek/hatch-vcs#readme)
