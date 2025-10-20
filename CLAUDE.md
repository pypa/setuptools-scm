# setuptools-scm Development Guide for AI Assistants

## Project Overview

**setuptools-scm monorepo** - Extract Python package versions from Git/Mercurial metadata.

- **Language**: Python 3.10+
- **Build**: setuptools, uv for dependency management
- **Quality**: pre-commit hooks (ruff, mypy strict), pytest with fixtures

### Structure
```
setuptools-scm/          # Setuptools integration (file finders, hooks)
├── src/setuptools_scm/  # Integration code
└── testing_scm/         # Setuptools-specific tests

vcs-versioning/          # Core VCS versioning (standalone library)
├── src/vcs_versioning/  # Core version inference
└── testing_vcs/         # Core functionality tests
```

## Quick Commands

```bash
# Setup
uv sync --all-packages --all-groups

# Tests (use -n12 for parallel execution)
uv run pytest -n12                              # all tests
uv run pytest setuptools-scm/testing_scm -n12   # setuptools tests only
uv run pytest vcs-versioning/testing_vcs -n12   # core tests only

# Quality (use pre-commit)
pre-commit run --all-files                      # run all quality checks
git commit                                      # pre-commit runs automatically

# Docs
uv run mkdocs serve       # local preview
uv run mkdocs build --clean --strict

# CLI
uv run python -m setuptools_scm              # version from current repo
uv run python -m vcs_versioning --help       # core CLI
```

## Code Conventions

### Typing
- **Strict mypy** - precise types, avoid `Any`
- Type all public functions/classes

### Style
- **Ruff** enforces all rules (lint + isort)
- Single-line imports, ordered by type
- Lines ≤88 chars where practical

### Testing
- Use project fixtures (`WorkDir`, `wd`, etc.)
- Warnings treated as errors
- Add `@pytest.mark.issue(id)` when fixing bugs

### Logging
- Log level info/debug in tests
- Minimal logging in library code

### General
- Small, focused functions
- Early returns preferred
- Explicit error messages
- Concise docstrings

## Project Rules

1. **Use `uv run pytest -n12`** to run tests (parallel execution)
2. **Use uv to manage dependencies** - don't use pip/conda
3. **Follow preexisting conventions** - match surrounding code style
4. **Use the fixtures** - `WorkDir`, `wd`, etc. for test repositories

### File Organization
- `setuptools-scm/testing_scm/` - setuptools integration tests
- `vcs-versioning/testing_vcs/` - core VCS functionality tests
- Add tests in the appropriate directory based on what layer you're testing

## Before Considering Done

- [ ] **Tests pass**: `uv run pytest -n12`
- [ ] **Pre-commit passes**: `pre-commit run --all-files` (ruff, mypy, etc.)
- [ ] **New behavior has tests** (use project fixtures)
- [ ] **Update docs** if user-facing changes
- [ ] **Add changelog fragment** (always use towncrier, never edit CHANGELOG.md directly)

## Key Files

- `CONTRIBUTING.md` - Release process with towncrier
- `TESTING.md` - Test organization and running
- `docs/` - User-facing documentation (mkdocs)
- `pyproject.toml` - Workspace config (pytest, mypy, ruff)
- `uv.lock` - Locked dependencies

## Common Patterns

### Version Schemes
Located in `vcs_versioning/_version_schemes.py`. Entry points in `pyproject.toml`.

### File Finders
In `setuptools_scm/_file_finders/`. Register as `setuptools.file_finders` entry point.
**Always active when setuptools-scm is installed** - even without version inference.

### Integration Hooks
- `infer_version()` - finalize_options hook (pyproject.toml projects)
- `version_keyword()` - setup.py `use_scm_version` parameter
- File finder - always registered, independent of versioning

## Changelog Management

**ALWAYS use towncrier fragments - NEVER edit CHANGELOG.md directly.**

Create fragments in `{project}/changelog.d/`:

```bash
# Bug fix (patch bump)
echo "Fix warning logic" > setuptools-scm/changelog.d/1231.bugfix.md

# New feature (minor bump)
echo "Add new scheme" > vcs-versioning/changelog.d/123.feature.md

# Breaking change (major bump)
echo "Remove deprecated API" > setuptools-scm/changelog.d/456.removal.md
```

**Fragment types**: `feature`, `bugfix`, `deprecation`, `removal`, `doc`, `misc`

## Debugging

```bash
# Check version inference
uv run python -m setuptools_scm

# With custom config
uv run python -m vcs_versioning --root . --version-scheme guess-next-dev

# Debug mode (set in tests or CLI)
SETUPTOOLS_SCM_DEBUG=1 uv run python -m setuptools_scm
```

---

**Documentation**: https://setuptools-scm.readthedocs.io/
**Repository**: https://github.com/pypa/setuptools-scm/
**Issues**: https://github.com/pypa/setuptools-scm/issues

