# Integrations

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

setuptools-scm provides the `no-local-version` local scheme and environment variable overrides to handle this scenario cleanly.

#### The Problem

By default, setuptools-scm generates version numbers like:
- `1.2.3.dev4+g1a2b3c4d5` (development version with git hash)
- `1.2.3+dirty` (dirty working directory)

These local version components (`+g1a2b3c4d5`, `+dirty`) prevent uploading to PyPI.

#### The Solution

Use the `SETUPTOOLS_SCM_OVERRIDES_FOR_${DIST_NAME}` environment variable to override the `local_scheme` to `no-local-version` when building for upload to PyPI.

### GitHub Actions Example

Here's a complete GitHub Actions workflow that:
- Runs tests on all branches
- Uploads development versions to test-PyPI from feature branches
- Uploads development versions to PyPI from the main branch (with no-local-version)
- Uploads tagged releases to PyPI (using exact tag versions)

```yaml title=".github/workflows/ci.yml"
name: CI/CD

on:
  push:
    branches: ["main", "develop"]
  pull_request:
    branches: ["main", "develop"]
  release:
    types: [published]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.8", "3.9", "3.10", "3.11", "3.12"]

    steps:
    - uses: actions/checkout@v4
      with:
        # Fetch full history for setuptools-scm
        fetch-depth: 0

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build pytest
        pip install -e .

    - name: Run tests
      run: pytest

  publish-test-pypi:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref != 'refs/heads/main'
    env:
      # Replace MYPACKAGE with your actual package name (normalized)
      # For package "my-awesome.package", use "MY_AWESOME_PACKAGE"
      SETUPTOOLS_SCM_OVERRIDES_FOR_MYPACKAGE: '{"local_scheme": "no-local-version"}'

    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.11"

    - name: Install build dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine

    - name: Build package
      run: python -m build

    - name: Upload to test-PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        repository-url: https://test.pypi.org/legacy/
        password: ${{ secrets.TEST_PYPI_API_TOKEN }}

  publish-pypi:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    env:
      # Replace MYPACKAGE with your actual package name (normalized)
      SETUPTOOLS_SCM_OVERRIDES_FOR_MYPACKAGE: '{"local_scheme": "no-local-version"}'

    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.11"

    - name: Install build dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine

    - name: Build package
      run: python -m build

    - name: Upload to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        password: ${{ secrets.PYPI_API_TOKEN }}

  publish-release:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'release'

    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.11"

    - name: Install build dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine

    - name: Build package
      run: python -m build

    - name: Upload to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        password: ${{ secrets.PYPI_API_TOKEN }}
```

### GitLab CI Example

Here's an equivalent GitLab CI configuration:

```yaml title=".gitlab-ci.yml"
stages:
  - test
  - publish

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip/

before_script:
  - python -m pip install --upgrade pip

test:
  stage: test
  image: python:3.11
  script:
    - pip install build pytest
    - pip install -e .
    - pytest
  parallel:
    matrix:
      - PYTHON_VERSION: ["3.8", "3.9", "3.10", "3.11", "3.12"]
  image: python:${PYTHON_VERSION}

publish-test-pypi:
  stage: publish
  image: python:3.11
  variables:
    TWINE_USERNAME: __token__
    TWINE_PASSWORD: $TEST_PYPI_API_TOKEN
    # Replace MYPACKAGE with your actual package name (normalized)
    SETUPTOOLS_SCM_OVERRIDES_FOR_MYPACKAGE: '{"local_scheme": "no-local-version"}'
  script:
    - pip install build twine
    - python -m build
    - twine upload --repository testpypi dist/*
  rules:
    - if: $CI_COMMIT_BRANCH != "main" && $CI_PIPELINE_SOURCE == "push"

publish-pypi:
  stage: publish
  image: python:3.11
  variables:
    TWINE_USERNAME: __token__
    TWINE_PASSWORD: $PYPI_API_TOKEN
    # Replace MYPACKAGE with your actual package name (normalized)
    SETUPTOOLS_SCM_OVERRIDES_FOR_MYPACKAGE: '{"local_scheme": "no-local-version"}'
  script:
    - pip install build twine
    - python -m build
    - twine upload dist/*
  rules:
    - if: $CI_COMMIT_BRANCH == "main" && $CI_PIPELINE_SOURCE == "push"

publish-release:
  stage: publish
  image: python:3.11
  variables:
    TWINE_USERNAME: __token__
    TWINE_PASSWORD: $PYPI_API_TOKEN
  script:
    - pip install build twine
    - python -m build
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
   SETUPTOOLS_SCM_OVERRIDES_FOR_MYPACKAGE='{"local_scheme": "no-local-version"}'
   ```

#### Alternative Approaches

**Option 1: pyproject.toml Configuration**

Instead of environment variables, you can configure this in your `pyproject.toml`:

```toml title="pyproject.toml"
[tool.setuptools_scm]
# Use no-local-version by default for CI builds
local_scheme = "no-local-version"
```

However, the environment variable approach is preferred for CI/CD as it allows different schemes for local development vs. CI builds.

#### Version Examples

**Development versions from main branch** (with `local_scheme = "no-local-version"`):
- Development commit: `1.2.3.dev4+g1a2b3c4d5` → `1.2.3.dev4` ✅ (uploadable to PyPI)
- Dirty working directory: `1.2.3+dirty` → `1.2.3` ✅ (uploadable to PyPI)

**Tagged releases** (without overrides, using default local scheme):
- Tagged commit: `1.2.3` → `1.2.3` ✅ (uploadable to PyPI)
- Tagged release on dirty workdir: `1.2.3+dirty` → `1.2.3+dirty` ❌ (should not happen in CI)

### Security Notes

- Store PyPI API tokens as repository secrets
- Use separate tokens for test-PyPI and production PyPI
- Consider using [Trusted Publishers](https://docs.pypi.org/trusted-publishers/) for enhanced security

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

**Fetch depth**: Always use `fetch-depth: 0` in GitHub Actions to ensure setuptools-scm has access to the full git history for proper version calculation.