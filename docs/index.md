# About


`setuptools_scm` extracts Python package versions from `git` or `hg` metadata
instead of declaring them as the version argument or in a SCM managed file.

Additionally `setuptools_scm` provides setuptools with a list of
files that are managed by the SCM (i.e. it automatically adds all
the SCM-managed files to the sdist). Unwanted files must be excluded
via `MANIFEST.in`.

## basic usage

### with setuptools

Note: `setuptools_scm>=8` intentionally doesn't depend on setuptools to ease non-setuptools usage.
Please ensure a recent version of setuptools (>=64) is installed.


```toml
# pyproject.toml
[build-system]
requires = [
    "setuptools>=64",
    "setuptools_scm>=8",
    "wheel",
]
[project]
name = "example"
# Important: Remove any existing version declaration
# version = "0.0.1"
dynamic = ["version"]
# more missing

[tool.setuptools_scm]

```


### with hatch

[Hatch-vcs](https://github.com/ofek/hatch-vcs) integrates with setuptools_scm
but provides its own configuration options,
please see its [documentation](https://github.com/ofek/hatch-vcs#readme)
