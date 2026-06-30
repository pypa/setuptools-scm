# Integrations

## dynamic-metadata

Any PEP 517 backend that supports the `tool.dynamic-metadata` array (as described in
[scikit-build/dynamic-metadata](https://github.com/scikit-build/dynamic-metadata)),
such as scikit-build-core 1.0+, can infer its version from VCS metadata using the
`vcs_versioning` provider shipped with vcs-versioning:

```toml title="pyproject.toml"
[build-system]
requires = ["scikit-build-core", "vcs-versioning"]
build-backend = "scikit_build_core.build"

[project]
name = "my-package"
dynamic = ["version"]

[tool.vcs-versioning]
# normal vcs-versioning options go here, e.g.
# local_scheme = "no-local-version"

[[tool.dynamic-metadata]]
provider = "vcs_versioning"
```

The provider always populates `version`. Version-scheme settings are read from
`[tool.vcs-versioning]`. You may also pass options inline in the
`[[tool.dynamic-metadata]]` table — any key there is forwarded as an override, so
this is equivalent to the `local_scheme` above:

```toml
[[tool.dynamic-metadata]]
provider = "vcs_versioning"
local_scheme = "no-local-version"
```

## ReadTheDocs

### Avoid having a dirty Git index

When building documentation on ReadTheDocs, file changes during the build process can cause setuptools-scm to detect a "dirty" working directory.

To avoid this issue, ReadTheDocs recommends using build customization to clean the Git state after checkout:

```yaml title=".readthedocs.yaml"
version: 2
build:
  os: "ubuntu-22.04"
  tools:
    python: "3.10"
  jobs:
    post_checkout:
      # Avoid setuptools-scm dirty Git index issues
      - git reset --hard HEAD
      - git clean -fdx
```

This ensures a clean Git working directory before setuptools-scm detects the version, preventing unwanted local version components.



Reference: [ReadTheDocs Build Customization - Avoid having a dirty Git index](https://docs.readthedocs.com/platform/stable/build-customization.html#avoid-having-a-dirty-git-index)


### Enforce fail on shallow repositories

ReadTheDocs may sometimes use shallow Git clones that lack the full history needed for proper version detection. You can use setuptools-scm's environment variable override system to enforce `fail_on_shallow` when building on ReadTheDocs:

```yaml title=".readthedocs.yaml"
version: 2
build:
  os: "ubuntu-22.04"
  tools:
    python: "3.10"
  jobs:
    post_checkout:
      # Avoid setuptools-scm dirty Git index issues
      - git reset --hard HEAD
      - git clean -fdx
      # Enforce fail_on_shallow for setuptools-scm
      - export SETUPTOOLS_SCM_OVERRIDES_FOR_${READTHEDOCS_PROJECT//-/_}='{scm.git.pre_parse="fail_on_shallow"}'
```

This configuration uses the `SETUPTOOLS_SCM_OVERRIDES_FOR_${DIST_NAME}` environment variable to override the `scm.git.pre_parse` setting specifically for your project when building on ReadTheDocs, forcing setuptools-scm to fail with a clear error if the repository is shallow.

## CI/CD and Package Publishing

### Publishing to PyPI from CI/CD

When publishing packages to PyPI or test-PyPI from CI/CD pipelines, you often need to remove local version components that are not allowed on public package indexes according to [PEP 440](https://peps.python.org/pep-0440/#local-version-identifiers).

setuptools-scm provides local scheme overrides to handle this scenario cleanly.

#### The Problem

By default, setuptools-scm generates version numbers like:

- `1.2.3.dev4+g1a2b3c4d5` (development version with git hash)
- `1.2.3+dirty` (dirty working directory)

These local version components (`+g1a2b3c4d5`, `+dirty`) prevent uploading to PyPI.

#### The Solution

Use the `SETUPTOOLS_SCM_OVERRIDES_FOR_${DIST_NAME}` environment variable to override the `local_scheme` when building for upload to PyPI.

For **release builds** use `no-local-version-strict` — it strips the local segment like `no-local-version` but additionally **fails the build** when the working tree is dirty, catching accidental pollution early.

For **development uploads** (test-PyPI, nightly) where the tree may be dirty, use `no-local-version` instead.

### GitHub Actions Example

Here's a complete GitHub Actions workflow following the
[PyPA recommended publishing guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/).
It uses:

- A **dedicated build job** with [`build-and-inspect-python-package`](https://github.com/hynek/build-and-inspect-python-package) (BAIPP) to build once and store artifacts
- **OIDC Trusted Publishers** for keyless, tokenless authentication to PyPI/test-PyPI
- Separate publish jobs that only download and upload the pre-built artifacts

```yaml title=".github/workflows/ci.yml"
name: CI/CD

on:
  push:
    branches: ["main"]
  pull_request:
  release:
    types: [published]

jobs:
  build:
    name: Build distribution packages
    runs-on: ubuntu-latest
    env:
      # Replace MYPACKAGE with your actual package name (normalized).
      # For package "my-awesome.package", use "MY_AWESOME_PACKAGE".
      # "strict" fails the build on dirty trees — catches accidental pollution.
      SETUPTOOLS_SCM_OVERRIDES_FOR_MYPACKAGE: '{local_scheme = "no-local-version-strict"}'

    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0

    - uses: hynek/build-and-inspect-python-package@v2

  test:
    needs: build
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]

    steps:
    - uses: actions/checkout@v4

    - name: Download built packages
      uses: actions/download-artifact@v4
      with:
        name: Packages
        path: dist/

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install built wheel and test dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pytest
        pip install dist/*.whl

    - name: Run tests
      run: pytest

  publish-test-pypi:
    name: Publish to test-PyPI
    needs: [build, test]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: test-pypi
    permissions:
      id-token: write

    steps:
    - name: Download built packages
      uses: actions/download-artifact@v4
      with:
        name: Packages
        path: dist/

    - name: Upload to test-PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        repository-url: https://test.pypi.org/legacy/

  publish-pypi:
    name: Publish to PyPI
    needs: [build, test]
    if: github.event_name == 'release'
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write

    steps:
    - name: Download built packages
      uses: actions/download-artifact@v4
      with:
        name: Packages
        path: dist/

    - name: Upload to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
```

### GitLab CI Example

Here's an equivalent GitLab CI configuration using a dedicated build stage with artifacts:

```yaml title=".gitlab-ci.yml"
stages:
  - build
  - test
  - publish

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip/

before_script:
  - python -m pip install --upgrade pip

build:
  stage: build
  image: python:3.12
  variables:
    # Replace MYPACKAGE with your actual package name (normalized)
    # "strict" fails the build on dirty trees — catches accidental pollution
    SETUPTOOLS_SCM_OVERRIDES_FOR_MYPACKAGE: '{local_scheme = "no-local-version-strict"}'
  script:
    - pip install build
    - python -m build
  artifacts:
    paths:
      - dist/

test:
  stage: test
  needs:
    - build
  parallel:
    matrix:
      - PYTHON_VERSION: ["3.10", "3.11", "3.12", "3.13"]
  image: python:${PYTHON_VERSION}
  script:
    - pip install pytest
    - pip install dist/*.whl
    - pytest

publish-test-pypi:
  stage: publish
  image: python:3.12
  dependencies:
    - build
  id_tokens:
    PYPI_ID_TOKEN:
      aud: testpypi
  script:
    - pip install twine
    - twine upload --repository testpypi dist/*
  rules:
    - if: $CI_COMMIT_BRANCH == "main" && $CI_PIPELINE_SOURCE == "push"

publish-pypi:
  stage: publish
  image: python:3.12
  dependencies:
    - build
  id_tokens:
    PYPI_ID_TOKEN:
      aud: pypi
  script:
    - pip install twine
    - twine upload dist/*
  rules:
    - if: $CI_COMMIT_TAG
```

### Configuration Details

#### Environment Variable Format

The environment variable `SETUPTOOLS_SCM_OVERRIDES_FOR_${DIST_NAME}` must be set where:

1. **`${DIST_NAME}`** is your package name normalized according to PEP 503:

    - Convert to uppercase
    - Replace hyphens and dots with underscores
    - Examples: `my-package` → `MY_PACKAGE`, `my.package` → `MY_PACKAGE`

2. **Value** must be a valid TOML inline table format:
   ```bash
   SETUPTOOLS_SCM_OVERRIDES_FOR_MYPACKAGE='{local_scheme = "no-local-version-strict"}'
   ```

#### Alternative Approaches

**Option 1: pyproject.toml Configuration**

Instead of environment variables, you can configure this in your `pyproject.toml`:

```toml title="pyproject.toml"
[tool.setuptools_scm]
# Fail on dirty trees and strip local version — recommended for release CI
local_scheme = "no-local-version-strict"
```

However, the environment variable approach is preferred for CI/CD as it allows different schemes for local development vs. CI builds.

#### Choosing a local scheme for CI

| Scheme | Dirty tree | Local segment | Use case |
|--------|-----------|---------------|----------|
| `no-local-version` | Silently allowed | Stripped | Dev/nightly uploads where dirty is acceptable |
| `no-local-version-strict` | **Build fails** | Stripped | Release CI — catches accidental pollution |
| `["fail-on-uncommitted-changes", "node-and-date"]` | **Build fails** | Kept (node + date) | When you want dirty protection with full local info |

#### Version Examples

**Development versions** (with `local_scheme = "no-local-version"`):

- Development commit: `1.2.3.dev4+g1a2b3c4d5` → `1.2.3.dev4` ✅ (uploadable to PyPI)
- Dirty working directory: `1.2.3+dirty` → `1.2.3` ✅ (uploadable to PyPI)

**Release versions** (with `local_scheme = "no-local-version-strict"`):

- Tagged commit: `1.2.3` → `1.2.3` ✅ (uploadable to PyPI)
- Tagged release on dirty workdir → **build fails** with `DirtyWorkingTreeError` ✅ (caught early)

### Security Notes

- Use [Trusted Publishers](https://docs.pypi.org/trusted-publishers/) (OIDC) instead of long-lived API tokens — this enables keyless authentication and digital attestations
- Configure separate PyPI environments (`pypi`, `test-pypi`) in your repository settings for environment protection rules
- See the [PyPA publishing guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/) for the full recommended setup

### Troubleshooting

**Package name normalization**: If your override isn't working, verify the package name normalization:

```python
import re
dist_name = "my-awesome.package"
normalized = re.sub(r"[-_.]+", "-", dist_name)
env_var_name = normalized.replace("-", "_").upper()
print(f"SETUPTOOLS_SCM_OVERRIDES_FOR_{env_var_name}")
# Output: SETUPTOOLS_SCM_OVERRIDES_FOR_MY_AWESOME_PACKAGE
```

**Fetch depth**: Always use `fetch-depth: 0` in GitHub Actions to ensure setuptools-scm has access to the full Git history for proper version calculation.
