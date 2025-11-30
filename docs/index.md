# About

`setuptools-scm` extracts Python package versions from `git` or `hg` metadata
instead of declaring them as the version argument
or in a Source Code Managed (SCM) managed file.

Additionally `setuptools-scm` provides `setuptools` with a list of
files that are managed by the SCM
(i.e. it automatically adds all the SCM-managed files to the sdist).
Unwanted files must be excluded via `MANIFEST.in`
or [configuring Git archive][git-archive-docs].

!!! warning "Automatic File Inclusion Behavior"

    **Important:** Simply installing `setuptools-scm` as a build dependency will automatically enable its file finder, which includes **all SCM-tracked files** in your source distributions. This happens even if you're not using setuptools-scm for versioning.

    - ✅ **Expected**: All Git/Mercurial tracked files will be included in your sdist
    - ⚠️ **Surprise**: This includes development files, configs, tests, docs, etc.
    - 🛠️ **Control**: Use `MANIFEST.in` to exclude unwanted files

    See the [File Finder Documentation](usage.md#file-finders-hook-makes-most-of-manifestin-unnecessary) for details.

[git-archive-docs]: usage.md#builtin-mechanisms-for-obtaining-version-numbers

## Architecture

`setuptools-scm` is built on top of [`vcs-versioning`](https://pypi.org/project/vcs-versioning/),
a standalone library that provides the core VCS version extraction and formatting functionality.

**vcs-versioning** (core library):
:   Handles version extraction from Git and Mercurial repositories, version scheme logic,
    tag parsing, and version formatting. These are universal concepts that work across
    different build systems and integrations.

**setuptools-scm** (integration layer):
:   Provides setuptools-specific features like build-time integration, automatic file
    finder registration, and version file generation during package builds.

!!! info "Understanding the documentation"

    Most configuration options documented here are **core vcs-versioning features** that
    work universally. Features specific to setuptools-scm integration (like automatic
    file finders or version file writing) are clearly marked throughout the documentation.

## Basic usage

### With setuptools

Note: `setuptools-scm>=8` intentionally doesn't depend on setuptools to ease non-setuptools usage.
Please ensure a recent version of setuptools is installed (minimum: >=61, recommended: >=80 for best compatibility).
Support for setuptools <80 is deprecated and will be removed in a future release.

**Simplified setup (recommended for basic usage):**

```toml title="pyproject.toml"
[build-system]
requires = ["setuptools>=80", "setuptools-scm[simple]>=8"]
build-backend = "setuptools.build_meta"

[project]
name = "example"
# Important: Remove any existing version declaration
# version = "0.0.1"
dynamic = ["version"]

# No additional configuration needed!
```

**With custom configuration:**

```toml title="pyproject.toml"
[build-system]
requires = ["setuptools>=80", "setuptools-scm>=8"]
build-backend = "setuptools.build_meta"

[project]
name = "example"
dynamic = ["version"]

[tool.setuptools_scm]
# Custom configuration options go here
```


!!! tip "Recommended Tag Format"

    Use the **"v" prefix** for your version tags for best compatibility:

    ```bash
    git tag v1.0.0
    git tag v1.1.0
    git tag v2.0.0-rc1
    ```

    This is a widely adopted convention that works well with setuptools-scm and other tools.
    See the [Version Tag Formats](usage.md#version-tag-formats) section for more details.


### With hatch

[Hatch-vcs](https://github.com/ofek/hatch-vcs) integrates with setuptools-scm
but provides its own configuration options,
please see its [documentation](https://github.com/ofek/hatch-vcs#readme)
