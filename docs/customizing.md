# Customizing

## providing project local version schemes

As the PEP-621 provides no way to specify local code as a build backend plugin,
setuptools_scm has to piggyback on setuptools for passing functions over.

To facilitate that one needs to write a `setup.py` file and
pass partial setuptools_scm configuration in via the use_scm_version keyword.

It's strongly recommended to experiment with using stock version schemes or creating plugins as package.
(This recommendation will change if there ever is something like build-time entrypoints).


``` { .python title="setup.py" file="docs/examples/version_scheme_code/setup.py" }
# we presume installed build dependencies
from __future__ import annotations

from setuptools import setup

from setuptools_scm import ScmVersion


def myversion_func(version: ScmVersion) -> str:
    from setuptools_scm.version import guess_next_version

    return version.format_next_version(guess_next_version, "{guessed}b{distance}")


setup(use_scm_version={"version_scheme": myversion_func})
```


``` { .python title="pyproject.toml" file="docs/examples/version_scheme_code/pyproject.toml" }
[build-system]
requires = [
  "setuptools>=64",
  "setuptools_scm>=8",
  "wheel",
]

[project]
name = "scm-example"
dynamic = [
  "version",
]

[tool.setuptools_scm]
```

- [ ] add a build block that adds example output
- [ ] correct config after [entangled mkdocs bug] is fixed

[entangled mkdocs bug]: https://github.com/entangled/mkdocs-plugin/issues/1