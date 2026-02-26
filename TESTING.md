# Testing Organization

This document describes the test organization in the setuptools-scm monorepo.

## Directory Structure

The repository contains two test suites:

- **`vcs-versioning/testing_vcs/`** - Core VCS versioning functionality tests
- **`setuptools-scm/testing_scm/`** - Setuptools integration and wrapper tests

## Separation Principle

Tests are organized by architectural layer:

### Core VCS Layer (`vcs-versioning/testing_vcs/`)

Tests for core version control system functionality:
- VCS backend operations (Git, Mercurial parsing)
- Version scheme and formatting logic
- Configuration validation
- Version inference
- Error handling
- Core utility functions

**When to add tests here:** If the functionality is in `vcs_versioning` package and doesn't depend on setuptools.

### Setuptools Integration Layer (`setuptools-scm/testing_scm/`)

Tests for setuptools-specific functionality:
- Setuptools hooks and entry points
- `setup.py` integration (` use_scm_version`)
- `pyproject.toml` reading and Configuration.from_file()
- File finding for setuptools (sdist integration)
- Distribution metadata
- setuptools-scm CLI wrapper

**When to add tests here:** If the functionality is in `setuptools_scm` package or requires setuptools machinery.

## Running Tests

### Run all tests
```bash
uv run pytest -n12
```

### Run core VCS tests only
```bash
uv run pytest vcs-versioning/testing_vcs -n12
```

### Run setuptools integration tests only
```bash
uv run pytest setuptools-scm/testing_scm -n12
```

### Run specific test file
```bash
uv run pytest vcs-versioning/testing_vcs/test_version_schemes.py -v
# Test the towncrier version scheme
uv run pytest vcs-versioning/testing_vcs/test_version_scheme_towncrier.py -v
```

## Test Fixtures

Both test suites use `vcs_versioning.test_api` as a pytest plugin, providing common test infrastructure:

- `WorkDir`: Helper for creating temporary test repositories
- `TEST_SOURCE_DATE`: Consistent test time for reproducibility
- `DebugMode`: Context manager for debug logging
- Repository fixtures: `wd`, `repositories_hg_git`, etc.

See `vcs-versioning/src/vcs_versioning/test_api.py` and `vcs-versioning/src/vcs_versioning/_test_utils.py` for details.

## Testing Release Workflows

### Testing the towncrier-fragments Version Scheme

The `towncrier-fragments` version scheme determines version bumps based on changelog fragments:

```bash
# Create test fragments
echo "Test feature" > setuptools-scm/changelog.d/1.feature.md
echo "Test bugfix" > setuptools-scm/changelog.d/2.bugfix.md

# Check what version would be generated
cd setuptools-scm
uv run python -m vcs_versioning --root .. --version-scheme towncrier-fragments
# Should show a minor bump (e.g., 9.3.0.dev...)

# Clean up test fragments
rm changelog.d/1.feature.md changelog.d/2.bugfix.md
```

### Testing Towncrier Build

Test changelog generation without committing:

```bash
cd setuptools-scm

# Dry-run: see what the changelog would look like
uv run towncrier build --version 9.3.0 --draft

# Build with keeping fragments (for testing)
uv run towncrier build --version 9.3.0 --keep
```

### Testing Version Bump Logic

Fragment types determine version bumps:

- **removal** → Major bump (X.0.0)
- **feature**, **deprecation** → Minor bump (0.X.0)
- **bugfix**, **doc**, **misc** → Patch bump (0.0.X)

Create different fragment types and verify the version scheme produces the expected version.

### Local Release Workflow Testing

You can test the release process locally (without actually creating tags):

```bash
# 1. Create test fragments
echo "Add new feature" > setuptools-scm/changelog.d/999.feature.md

# 2. Query version scheme
cd setuptools-scm
NEXT_VERSION=$(uv run python -m vcs_versioning --root .. --version-scheme towncrier-fragments --local-scheme no-local-version 2>/dev/null | grep -oP '^\d+\.\d+\.\d+')
echo "Next version: $NEXT_VERSION"

# 3. Build changelog (dry-run)
uv run towncrier build --version "$NEXT_VERSION" --draft

# 4. Clean up
rm changelog.d/999.feature.md
cd ..
```

### Workflow Validation

Before merging workflow changes:

1. Validate YAML syntax:
   ```bash
   # If you have actionlint installed
   actionlint .github/workflows/*.yml
   ```

2. Check workflow conditions match your expectations:
   - Tag filters in `python-tests.yml`
   - Label checks in `create-release-tags.yml`

3. Test in a fork with reduced scope (test project, Test PyPI)

## Migration Notes

File finders remain in setuptools-scm because they're setuptools integration (registered as `setuptools.file_finders` entry points), not core VCS functionality.

For deeper unit test conversions beyond basic reorganization, see `setuptools-scm/testing_scm/INTEGRATION_MIGRATION_PLAN.md`.

