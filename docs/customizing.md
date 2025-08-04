# Customizing

## providing project local version schemes

As PEP 621 provides no way to specify local code as a build backend plugin,
setuptools-scm has to piggyback on setuptools for passing functions over.

To facilitate that one needs to write a `setup.py` file and
pass partial setuptools-scm configuration in via the use_scm_version keyword.

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


``` { .toml title="pyproject.toml" file="docs/examples/version_scheme_code/pyproject.toml" }
[build-system]
requires = ["setuptools>=80", "setuptools-scm>=8"]  # setuptools>=61 minimum, >=80 recommended
build-backend = "setuptools.build_meta"

[project]
name = "scm-example"
dynamic = [
  "version",
]

[tool.setuptools_scm]
```

- [ ] add a build block that adds example output




##  Importing in setup.py

With the pep 517/518 build backend, setuptools-scm is importable from `setup.py`

``` { .python title="setup.py" }
from setuptools import setup
from setuptools_scm.version import get_local_dirty_tag

def clean_scheme(version):
    return get_local_dirty_tag(version) if version.dirty else '+clean'

setup(use_scm_version={'local_scheme': clean_scheme})
```



## alternative version classes

::: setuptools_scm.NonNormalizedVersion
