# Usage

## At build time

!!! note "Setuptools Version Requirements"
    setuptools-scm requires setuptools 61 or later (minimum), but recommends >=80 for best compatibility.
    Support for setuptools <80 is deprecated and will be removed in a future release.
    The examples below use `setuptools>=80` as the recommended version.

There are two ways to configure `setuptools-scm` at build time, depending on your needs:

### Automatic Configuration (Recommended for Simple Cases)

For projects that don't need custom configuration, simply include `setuptools-scm`
in your build requirements:

```toml title="pyproject.toml"
[build-system]
requires = ["setuptools>=80", "setuptools-scm>=8"]
build-backend = "setuptools.build_meta"

[project]
# version = "0.0.1"  # Remove any existing version parameter.
dynamic = ["version"]
```

**That's it!** Starting with setuptools-scm 8.1+, if `setuptools_scm` (or `setuptools-scm`)
is present in your `build-system.requires`, setuptools-scm will automatically activate
with default settings.

### Explicit Configuration

If you need to customize setuptools-scm behavior, use the `tool.setuptools_scm` section:

```toml title="pyproject.toml"
[build-system]
requires = ["setuptools>=80", "setuptools-scm>=8"]
build-backend = "setuptools.build_meta"

[project]
# version = "0.0.1"  # Remove any existing version parameter.
dynamic = ["version"]

[tool.setuptools_scm]
# Configure custom options here (version schemes, file writing, etc.)
version_file = "src/mypackage/_version.py"

# Example: Git-specific configuration
[tool.setuptools_scm.scm.git]
pre_parse = "fail_on_missing_submodules"  # Fail if submodules are not initialized
describe_command = "git describe --dirty --tags --long --exclude *js*"  # Custom describe command
```

Both approaches will work with projects that support PEP 518 ([pip](https://pypi.org/project/pip) and
[pep517](https://pypi.org/project/pep517/)).
Tools that still invoke `setup.py` must ensure build requirements are installed

!!! info "How Automatic Detection Works"

    When setuptools-scm is listed in `build-system.requires`, it automatically detects this during the build process and activates with default settings. This means:

    - ✅ **Automatic activation**: No `[tool.setuptools_scm]` section needed
    - ✅ **Default behavior**: Uses standard version schemes and SCM detection
    - ✅ **Error handling**: Provides helpful error messages if configuration is missing
    - ⚙️ **Customization**: Add `[tool.setuptools_scm]` section when you need custom options

    Both package names are detected: `setuptools_scm` and `setuptools-scm` (with dash).

### Version files

Version files can be created with the ``version_file`` directive.

```toml title="pyproject.toml"
...
[tool.setuptools_scm]
version_file = "pkg/_version.py"
```
Where ``pkg`` is the name of your package.

Unless the small overhead of introspecting the version at runtime via
`importlib.metadata` is a concern or you need a version file in an
alternative format such as plain-text (see ``version_file_template``)
you most likely do _not_ need to write a separate version file; see
the runtime discussion below for more details.

## As cli tool

If you need to confirm which version string is being generated
or debug the configuration, you can install
[setuptools-scm](https://github.com/pypa/setuptools-scm)
directly in your working environment and run:

```commandline
$ python -m setuptools_scm # example from running local after changes
7.1.1.dev149+g5197d0f.d20230727
```

 and to list all tracked by the scm:

```commandline
$ python -m setuptools_scm ls # output trimmed for brevity
./LICENSE
...
./src/setuptools_scm/__init__.py
./src/...
...
```

!!! note "Committed files only"

    currently only committed files are listed, this might change in the future

!!! warning "sdists/archives don't provide file lists"

    Currently there is no builtin mechanism
    to safely transfer the file lists to sdists or obtaining them from archives.
    Coordination for setuptools and hatch is ongoing.

To explore other options, try

```commandline
$ python -m setuptools_scm --help
```

## At runtime

### Python Metadata

The standard method to retrieve the version number at runtime is via
[PEP-0566](https://www.python.org/dev/peps/pep-0566/) metadata using
``importlib.metadata`` from the standard library (added in Python 3.8)
or the
[`importlib_metadata`](https://pypi.org/project/importlib-metadata/)
backport for earlier versions:

```python title="package_name/__init__.py"
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("package-name")
except PackageNotFoundError:
    # package is not installed
    pass
```

### Via your version file

If you have opted to create a Python version file via the standard
template, you can import that file, where you will have a ``version``
string and a ``version_tuple`` tuple with elements corresponding to
the version tags.

```python title="Using package_name/_version.py"
import package_name._version as v

print(v.version)
print(v.version_tuple)
```

### Via setuptools_scm (strongly discouraged)

While the most simple **looking** way to use `setuptools_scm` at
runtime is:

```python
from setuptools_scm import get_version
version = get_version()
```

it is strongly discouraged to call directly into `setuptools_scm` over
the standard Python `importlib.metadata`.

In order to use `setuptools_scm` from code that is one directory deeper
than the project's root, you can use:

```python
from setuptools_scm import get_version
version = get_version(root='..', relative_to=__file__)
```

For legacy configurations or when working with extracted archives (like PyPI tarballs),
you may need to specify a `fallback_root` parameter. This is particularly useful
for legacy Sphinx configurations that use `get_version()` instead of getting the
version from the installed package:

```python
from setuptools_scm import get_version
# For legacy Sphinx conf.py that needs to work both in development and from archives
version = get_version(root='..', fallback_root='..', relative_to=__file__)
```

The `fallback_root` parameter specifies the directory to use when the SCM metadata
is not available (e.g., in extracted tarballs), while `root` is used when SCM
metadata is present.

### Usage from Sphinx

The recommended approach for Sphinx configurations is to use the installed package metadata:

``` {.python file=docs/.entangled/sphinx_conf.py}
from importlib.metadata import version as get_version
release: str = get_version("package-name")
# for example take major/minor
version: str = ".".join(release.split('.')[:2])
```

The underlying reason is that services like *Read the Docs* sometimes change
the working directory for good reasons and using the installed metadata
prevents using needless volatile data there.

!!! note "Legacy Sphinx configurations"

    If you have a legacy Sphinx configuration that still uses `setuptools_scm.get_version()`
    directly (instead of `importlib.metadata`), you may need to use the `fallback_root`
    parameter to ensure it works both in development and when building from archives:

    ```python
    from setuptools_scm import get_version
    # Legacy approach - use fallback_root for archive compatibility
    release = get_version(root='..', fallback_root='..', relative_to=__file__)
    version = ".".join(release.split('.')[:2])
    ```

    However, it's strongly recommended to migrate to the `importlib.metadata` approach above.


### With Docker/Podman


In some situations, Docker may not copy the `.git`  into the container when
building images. Because of this, builds with version inference may fail.

The following snippet exposes the external `.git` directory without copying.
This allows the version to be inferred properly form inside the container
without copying the entire `.git` folder into the container image.

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
Note that `SETUPTOOLS_SCM_PRETEND_VERSION_FOR_${DIST_NAME}`
is preferred over `SETUPTOOLS_SCM_PRETEND_VERSION`.



## Default versioning scheme

In the standard configuration `setuptools-scm` takes a look at three things:

1. latest tag (with a version number)
2. the distance to this tag (e.g. number of revisions since latest tag)
3. workdir state (e.g. uncommitted changes since latest tag)

and uses roughly the following logic to render the version:


| distance | state     | format                                                               |
|----------|-----------|----------------------------------------------------------------------|
| no       | unchanged | `{tag}`                                                              |
| yes      | unchanged | `{next_version}.dev{distance}+{scm letter}{revision hash}`           |
| no       | changed   | `{tag}+dYYYYMMDD`                                                    |
| yes      | changed   | `{next_version}.dev{distance}+{scm letter}{revision hash}.dYYYYMMDD` |

where `{next_version}` is the next version number after the latest tag

The next version is calculated by adding `1` to the last numeric component of
the tag.

For Git projects, the version relies on  [git describe](https://git-scm.com/docs/git-describe),
so you will see an additional `g` prepended to the `{revision hash}`.


## Version Tag Formats

setuptools-scm automatically detects version information from SCM tags. The default tag regex
supports a wide variety of tag formats, with the **"v" prefix being recommended** for clarity
and consistency.

### Recommended Tag Format

**Use the "v" prefix for version tags:**

```bash
git tag v1.0.0        # Recommended
git tag v2.1.3
git tag v1.0.0-alpha1
git tag v1.0.0-rc1
```

### Supported Tag Formats

setuptools-scm's default tag regex supports:

- **Version prefix**: `v` or `V` (optional, but recommended)
- **Project prefix**: Optional project name followed by dashes (e.g., `myproject-v1.0.0`)
- **Version number**: Standard semantic versioning patterns
- **Pre-release suffixes**: Alpha, beta, RC versions
- **Build metadata**: Anything after `+` is ignored

**Examples of valid tags:**
```bash
# Recommended formats (with v prefix)
v1.0.0
v2.1.3
v1.0.0-alpha1
v1.0.0-beta2
v1.0.0-rc1
v1.2.3-dev
V1.0.0              # Capital V also works

# Project-prefixed formats
myproject-v1.0.0
my-lib-v2.1.0

# Without v prefix (supported but not recommended)
1.0.0
2.1.3
1.0.0-alpha1

# With build metadata (metadata after + is ignored)
v1.0.0+build.123
v1.0.0+20240115
```

### Why Use the "v" Prefix?

1. **Clarity**: Makes it immediately obvious that the tag represents a version
2. **Convention**: Widely adopted standard across the software industry
3. **Git compatibility**: Works well with git's tag sorting and filtering
4. **Tool compatibility**: Many other tools expect version tags to have a "v" prefix

### Custom Tag Patterns

If you need different tag patterns, you can customize the tag regex:

```toml title="pyproject.toml"
[tool.setuptools_scm]
tag_regex = "^release-(?P<version>[0-9]+\\.[0-9]+\\.[0-9]+)$"
```

## Node ID Prefixes

setuptools-scm automatically prepends identifying characters to node IDs (commit/revision hashes)
to distinguish between different SCM systems:

- **Git repositories**: Node IDs are prefixed with `g` (e.g., `g1a2b3c4d5`)
- **Mercurial repositories**: Node IDs are prefixed with `h` (e.g., `h1a2b3c4d5`)

This prefixing serves several purposes:

1. **SCM identification**: Makes it clear which version control system was used
2. **Consistency**: Ensures predictable node ID format across different SCM backends
3. **Debugging**: Helps identify the source SCM when troubleshooting version issues

The prefixes are automatically added by setuptools-scm and should be included when manually
specifying node IDs in environment variables like `SETUPTOOLS_SCM_PRETEND_METADATA`.

**Examples:**
```bash
# Git node ID
1.0.0.dev5+g1a2b3c4d5

# Mercurial node ID
1.0.0.dev5+h1a2b3c4d5
```

!!! note

    According to [PEP 440](https://peps.python.org/pep-0440/#local-version-identifiers>),
    if a version includes a local component, the package cannot be published to public
    package indexes like PyPI or TestPyPI. The disallowed version segments may
    be seen in auto-publishing workflows or when a configuration mistake is made.

    However, some package indexes such as devpi or other alternatives allow local
    versions. Local version identifiers must comply with [PEP 440](https://peps.python.org/pep-0440/#local-version-identifiers>).

## Semantic Versioning (SemVer)

Due to the default behavior it's necessary to always include a
patch version (the `3` in `1.2.3`), or else the automatic guessing
will increment the wrong part of the SemVer (e.g. tag `2.0` results in
`2.1.devX` instead of `2.0.1.devX`). So please make sure to tag
accordingly.


## Builtin mechanisms for obtaining version numbers

1. the SCM itself (Git/Mercurial)
2. `.hg_archival` files (Mercurial archives)
3. `.git_archival.txt` files (Git archives, see subsection below)
4. `PKG-INFO`


### Git archives

Git archives are supported, but require specific setup and understanding of how they work with package building.

#### Overview

When you create a `.git_archival.txt` file in your repository, it enables setuptools-scm to extract version information from git archives (e.g., GitHub's source downloads). However, this file contains template placeholders that must be expanded by `git archive` - they won't work when building directly from your working directory.

#### Setting up git archival support

You can generate a `.git_archival.txt` file using the setuptools-scm CLI:

```commandline
# Generate a stable archival file (recommended for releases)
$ python -m setuptools_scm create-archival-file --stable

# Generate a full archival file with all metadata (use with caution)
$ python -m setuptools_scm create-archival-file --full
```

Alternatively, you can create the file manually:

**Stable version (recommended):**
```{ .text file=".git_archival.txt"}
node: $Format:%H$
node-date: $Format:%cI$
describe-name: $Format:%(describe:tags=true,match=*[0-9]*)$
```

**Full version (with branch information - can cause instability):**
```{ .text file=".git_archival.txt"}
# WARNING: Including ref-names can make archive checksums unstable
# after commits are added post-release. Use only if describe-name is insufficient.
node: $Format:%H$
node-date: $Format:%cI$
describe-name: $Format:%(describe:tags=true,match=*[0-9]*)$
ref-names: $Format:%D$
```

Feel free to alter the `match` field in `describe-name` to match your project's
tagging style.

!!! note

    If your git host provider does not properly expand `describe-name`, you may
    need to include `ref-names: $Format:%D$`. But **beware**, this can often
    lead to the git archive's checksum changing after a commit is added
    post-release. See [this issue][git-archive-issue] for more details.


``` {.text file=".gitattributes"}
.git_archival.txt  export-subst
```

Finally, commit both files:
```commandline
$ git add .git_archival.txt .gitattributes && git commit -m "add git archive support"
```

#### Understanding the warnings

If you see warnings like these when building your package:

```
UserWarning: git archive did not support describe output
UserWarning: unprocessed git archival found (no export subst applied)
```

This typically happens when:

1. **Building from working directory**: You're running `python -m build` directly in your repository
2. **Sdist extraction**: A build tool extracts your sdist to build wheels, but the extracted directory isn't a git repository

#### Recommended build workflows

**For development builds:**
Exclude `.git_archival.txt` from your package to avoid warnings:

```{ .text file="MANIFEST.in"}
# Exclude archival file from development builds
exclude .git_archival.txt
```

**For release builds from archives:**
Build from an actual git archive to ensure proper template expansion:

```commandline
# Create archive from a specific tag/commit
$ git archive --output=../source_archive.tar v1.2.3
$ cd ..
$ tar -xf source_archive.tar
$ cd extracted_directory/
$ python -m build .
```

**For automated releases:**
Many CI systems and package repositories (like GitHub Actions) automatically handle this correctly when building from git archives.

#### Integration with package managers

**MANIFEST.in exclusions:**
```{ .text file="MANIFEST.in"}
# Exclude development files from packages
exclude .git_archival.txt
exclude .gitattributes
```


```{ .text file=".gitattributes"}
# Archive configuration
.git_archival.txt  export-subst
.gitignore         export-ignore
```

#### Troubleshooting

**Problem: "unprocessed git archival found" warnings**
- ✅ **Solution**: Add `exclude .git_archival.txt` to `MANIFEST.in` for development builds
- ✅ **Alternative**: Build from actual git archives for releases

**Problem: "git archive did not support describe output" warnings**
- ℹ️ **Information**: This is expected when `.git_archival.txt` contains unexpanded templates
- ✅ **Solution**: Same as above - exclude file or build from git archives

**Problem: Version detection fails in git archives**
- ✅ **Check**: Is `.gitattributes` configured with `export-subst`?
- ✅ **Check**: Are you building from a properly created git archive?
- ✅ **Check**: Does your git hosting provider support archive template expansion?

!!! warning "Branch Names and Archive Stability"

    Including `ref-names: $Format:%D$` in your `.git_archival.txt` can make archive checksums change when new commits are added to branches referenced in the archive. This primarily affects GitHub's automatic source archives. Use the stable format (without `ref-names`) unless you specifically need branch information and understand the stability implications.

!!! note "Version Files"

    If you are creating a `_version.py` file, it should not be kept in version control. Add it to `.gitignore`:
    ```
    # Generated version file
    src/mypackage/_version.py
    ```

[git-archive-issue]: https://github.com/pypa/setuptools-scm/issues/806

### File finders hook makes most of `MANIFEST.in` unnecessary

!!! warning "Automatic File Inclusion"

    **`setuptools-scm` automatically provides a setuptools file finder by default.** This means that when you install setuptools-scm, it will automatically include **all SCM-tracked files** in your source distributions (sdist) without requiring a `MANIFEST.in` file.

    This automatic behavior can be surprising if you're not expecting it. The file finder is active as soon as setuptools-scm is installed in your build environment.

`setuptools-scm` implements a [file_finders] entry point
which returns all files tracked by your SCM.
This eliminates the need for a manually constructed `MANIFEST.in` in most cases where this
would be required when not using `setuptools-scm`.

[file_finders]: https://setuptools.pypa.io/en/stable/userguide/extension.html

#### How it works

1. **Automatic Discovery**: When building source distributions (`python -m build --sdist`), setuptools automatically calls the `setuptools-scm` file finder
2. **SCM Integration**: The file finder queries your SCM (Git/Mercurial) for all tracked files
3. **Inclusion**: All tracked files are automatically included in the sdist

#### Controlling file inclusion

**To exclude unwanted files:**

1. **Use `MANIFEST.in`** to exclude specific files/patterns:
   ```
   exclude development.txt
   recursive-exclude tests *.pyc
   ```

2. **Configure Git archive** (for Git repositories):
   ```bash
   # Add to .gitattributes
   tests/ export-ignore
   *.md export-ignore
   ```

3. **Use `.hgignore`** or **Mercurial archive configuration** (for Mercurial repositories)

#### Troubleshooting

**Problem: Unwanted files in my package**
- ✅ **Solution**: Add exclusions to `MANIFEST.in`
- ✅ **Alternative**: Use Git/Mercurial archive configuration

**Problem: Missing files in package**
- ✅ **Check**: Are the files tracked in your SCM?
- ✅ **Solution**: `git add` missing files or override with `MANIFEST.in`

**Problem: File finder not working**
- ✅ **Check**: Is setuptools-scm installed in your build environment?
- ✅ **Check**: Are you in a valid SCM repository?

### Timestamps for Local Development Versions

!!! info "Improved Timestamp Behavior"

    When your working directory has uncommitted changes (dirty), setuptools-scm now uses the **actual modification time of changed files** instead of the current time for local version schemes like `node-and-date`.

    **Before**: Dirty working directories always used current time (`now`)
    **Now**: Uses the latest modification time of changed files, falling back to current time only if no changed files are found

    This provides more stable and meaningful timestamps that reflect when you actually made changes to your code.

**How it works:**

1. **Clean repository**: Uses commit timestamp from SCM
2. **Dirty repository**: Uses latest modification time of changed files
3. **Fallback**: Uses current time if no modification times can be determined

**Benefits:**

- More stable builds during development
- Timestamps reflect actual change times
- Better for reproducible development workflows
