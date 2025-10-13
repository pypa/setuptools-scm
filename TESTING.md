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
```

## Test Fixtures

Both test suites use `vcs_versioning.test_api` as a pytest plugin, providing common test infrastructure:

- `WorkDir`: Helper for creating temporary test repositories
- `TEST_SOURCE_DATE`: Consistent test time for reproducibility
- `DebugMode`: Context manager for debug logging
- Repository fixtures: `wd`, `repositories_hg_git`, etc.

See `vcs-versioning/src/vcs_versioning/test_api.py` and `vcs-versioning/src/vcs_versioning/_test_utils.py` for details.

## Migration Notes

File finders remain in setuptools-scm because they're setuptools integration (registered as `setuptools.file_finders` entry points), not core VCS functionality.

For deeper unit test conversions beyond basic reorganization, see `setuptools-scm/testing_scm/INTEGRATION_MIGRATION_PLAN.md`.

