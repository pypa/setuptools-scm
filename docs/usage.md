# Usage

## at build time

The preferred way to configure `setuptools_scm` is to author
settings in the `tool.setuptools_scm` section of `pyproject.toml`.

It's considered necessary to use a setuptools version released after 2022.

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=62", "setuptools_scm[toml]>=8.0"]

[project]
# version = "0.0.1"  # Remove any existing version parameter.
dynamic = ["version"]

[tool.setuptools_scm]
# can be empty if no extra settings are needed, presence enables setuptools_scm
```

That will be sufficient to require `setuptools_scm` for projects
that support PEP 518 ([pip](https://pypi.org/project/pip) and
[pep517](https://pypi.org/project/pep517/)).
Tools that still invoke `setup.py` must ensure build requirements are installed

### version files

```toml
# pyproject.toml
...
[tool.setuptools_scm]
version_file = "pkg/_version.py"
```
Where ``pkg`` is the name of your package.


.. code-block:: shell

    $ python -m setuptools_scm

    # To explore other options, try:
    $ python -m setuptools_scm --help


## as cli tool

If you need to confirm which version string is being generated
or debug the configuration, you can install
[setuptools-scm](https://github.com/pypa/setuptools_scm)
directly in your working environment and run:

```commandline
$ python -m setuptools_scm # example from running local after changes
7.1.1.dev149+g5197d0f.d20230727
```

 and to list all tracked by the scm:

```commandline
$ python -m setuptools_scm ls # output trimmed for brevity
./LICESE
...
./src/setuptools_scm/__init__.py
./src/...
...
```

!!! note "committed files only"

    currently only committed files are listed, this might change in the future

!!! warning "sdists/archives don't provide file lists"

    currently there is no builtin mechanism
    to safely transfer the file lists to sdists or obtaining them from archives
    coordination for setuptools and hatch is ongoing

## at runtime (strongly discouraged)

the most simple **looking** way to use `setuptools_scm` at runtime is:

```python
from setuptools_scm import get_version
version = get_version()
```


In order to use `setuptools_scm` from code that is one directory deeper
than the project's root, you can use:

```python
from setuptools_scm import get_version
version = get_version(root='..', relative_to=__file__)
```


## python package metadata




### version at runtime
-------------------------------------

If you have opted not to hardcode the version number inside the package,
you can retrieve it at runtime from PEP-0566_ metadata using
``importlib.metadata`` from the standard library (added in Python 3.8)
or the `importlib_metadata`_ backport:

```python
# contents of package_name/__init__.py
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("package-name")
except PackageNotFoundError:
    # package is not installed
    pass
```

.. _PEP-0566: https://www.python.org/dev/peps/pep-0566/
.. _importlib_metadata: https://pypi.org/project/importlib-metadata/


### Usage from Sphinx
-----------------

``` {.python file=docs/.entangled/sphinx_conf.py}
from importlib.metadata import version as get_version
release: str = get_version('setuptools_scm')
# for example take major/minor
version: str = ".".join(release.split('.')[:2])
```

The underlying reason is, that services like *Read the Docs* sometimes change
the working directory for good reasons and using the installed metadata
prevents using needless volatile data there.


## with docker/podman


By default, docker will not copy the `.git`  folder into your container.
Therefore, builds with version inference might fail.
Consequently, you can use the following snippet to infer the version from
the host os without copying the entire `.git` folder to your Dockerfile.

```dockerfile
RUN --mount=source=.git,target=.git,type=bind \
    pip install --no-cache-dir -e .
```
However, this build step introduces a dependency to the state of your local
`.git` folder the build cache and triggers the long-running pip install process on every build.
To optimize build caching, one can use an environment variable to pretend a pseudo
version that is used to cache the results of the pip install process:


```dockerfile
FROM python
COPY pyproject.toml
ARG PSEUDO_VERSION=1 # strongly recommended to update based on git describe
RUN SETUPTOOLS_SCM_PRETEND_VERSION_FOR_MY_PACKAGE=${PSEUDO_VERSION} pip install -e .[test]
RUN --mount=source=.git,target=.git,type=bind pip install -e .
```

Note that running this Dockerfile requires docker with BuildKit enabled
[docs](https://github.com/moby/buildkit/blob/v0.8.3/frontend/dockerfile/docs/syntax.md).

To avoid BuildKit and mounting of the .git folder altogether, one can also pass the desired
version as a build argument.
Note that `SETUPTOOLS_SCM_PRETEND_VERSION_FOR_${NORMALIZED_DIST_NAME}`
is preferred over `SETUPTOOLS_SCM_PRETEND_VERSION`.
