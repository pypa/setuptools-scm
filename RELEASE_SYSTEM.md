# Release System Implementation Summary

This document summarizes the towncrier-based release system implemented for the setuptools-scm monorepo.

## What Was Implemented

### 1. Towncrier Configuration ✅

**Files Modified:**
- `pyproject.toml` - Added towncrier to release dependency group
- `setuptools-scm/pyproject.toml` - Added towncrier configuration
- `vcs-versioning/pyproject.toml` - Added towncrier configuration with entry point for `towncrier-fragments` version scheme

**Configuration includes:**
- Fragment types: `removal`, `deprecation`, `feature`, `bugfix`, `doc`, `misc`
- Automatic version bump determination based on fragment types
- Issue link formatting for GitHub

### 2. Changelog Fragment Directories ✅

**Created:**
- `setuptools-scm/changelog.d/` - With template, README, and .gitkeep
- `vcs-versioning/changelog.d/` - With template, README, and .gitkeep
- `setuptools-scm/CHANGELOG.md` - Added towncrier start marker
- `vcs-versioning/CHANGELOG.md` - Created with towncrier start marker

### 3. Fragment-Based Version Scheme ✅

**New File:** `vcs-versioning/src/vcs_versioning/_version_schemes_towncrier.py`

The `towncrier-fragments` version scheme:
- Analyzes `changelog.d/` for fragment types
- Determines version bump: major (removal) → minor (feature/deprecation) → patch (bugfix/doc/misc)
- Falls back to `guess-next-dev` if no fragments
- Works consistently in both development and release contexts
- **Single source of truth** for version determination - no duplicate logic in scripts!

**Entry Point Added:** `vcs_versioning.pyproject.toml`
```toml
"towncrier-fragments" = "vcs_versioning._version_schemes_towncrier:version_from_fragments"
```

**Tests:** `vcs-versioning/testing_vcs/test_version_scheme_towncrier.py`
- 33 comprehensive tests covering all fragment types and version bump logic
- Tests precedence (removal > feature > bugfix)
- Tests edge cases (0.x versions, missing directories, dirty working tree)
- All tests passing ✅

### 4. GitHub Workflows ✅

#### Release Proposal Workflow
**File:** `.github/workflows/release-proposal.yml`

- **Trigger:** Manual workflow_dispatch with checkboxes for which projects to release
- **Process:**
  1. Checks for changelog fragments in each project
  2. Uses `vcs-versioning` CLI to query version scheme (no custom scripts!)
  3. Runs `towncrier build` with the determined version
  4. Creates/updates release PR
  5. Automatically labels PR with `release:setuptools-scm` and/or `release:vcs-versioning`

#### Tag Creation Workflow
**File:** `.github/workflows/create-release-tags.yml`

- **Trigger:** PR merge to main with release labels
- **Process:**
  1. Detects which projects to release from PR labels
  2. Extracts version from updated CHANGELOG.md
  3. Creates project-prefixed tags: `setuptools-scm-vX.Y.Z`, `vcs-versioning-vX.Y.Z`
  4. Creates GitHub releases with changelog excerpts
  5. Tag push triggers PyPI upload

#### Modified Upload Workflow
**File:** `.github/workflows/python-tests.yml`

- Split `dist_upload` into separate jobs per project:
  - `dist_upload_setuptools_scm` - Only triggers on `setuptools-scm-v*` tags
  - `dist_upload_vcs_versioning` - Only triggers on `vcs-versioning-v*` tags
- Split `upload-release-assets` similarly
- Prevents accidental uploads of wrong packages

### 5. Reusable Workflow for Other Projects ✅

**File:** `.github/workflows/reusable-towncrier-release.yml`

Reusable workflow that other projects can reference:
```yaml
jobs:
  release:
    uses: pypa/setuptools-scm/.github/workflows/reusable-towncrier-release.yml@main
    with:
      project_name: my-project
      project_directory: ./
```

**Documentation:** `.github/workflows/README.md`

### 6. Helper Scripts ✅

**Only one simple script:**
- `.github/scripts/extract_version.py` - Extracts version from CHANGELOG.md after towncrier builds it

**Removed duplicate logic:**
- ❌ No version bump calculation scripts
- ❌ No duplicate version determination logic
- ❌ No fallback values or default versions
- ✅ Version scheme is the **single source of truth**
- ✅ Workflows fail explicitly if required data is missing

### 7. Comprehensive Documentation ✅

**Created:**
- `CONTRIBUTING.md` - Complete guide for contributors
  - How to add changelog fragments
  - Fragment types and naming conventions
  - Release process walkthrough
  - Benefits and architecture

**Updated:**
- `TESTING.md` - Added sections on:
  - Testing the version scheme locally
  - Testing towncrier builds
  - Testing release workflows
  - Workflow validation

## How It Works

### For Contributors

1. Make your changes
2. Create a changelog fragment:
   ```bash
   echo "Add support for feature X" > setuptools-scm/changelog.d/123.feature.md
   ```
3. Commit and create PR
4. During development, version reflects the next release:
   ```
   9.3.0.dev5+g1234567  # Next version will be 9.3.0
   ```

### For Maintainers

1. **Trigger Release Proposal:**
   - Go to Actions → "Create Release Proposal"
   - Select projects to release
   - Workflow creates labeled PR with updated changelog

2. **Review PR:**
   - Check changelog entries
   - Verify version numbers
   - Ensure tests pass

3. **Merge PR:**
   - Merge triggers tag creation automatically
   - Tags trigger PyPI upload
   - Done!

## Key Benefits

✅ **No custom scripts** - Version scheme handles all logic
✅ **Consistent versioning** - Development and release use same scheme
✅ **Manual approval** - PRs provide human review gate
✅ **Atomic releases** - Tied to merge commits
✅ **Project-specific tags** - `setuptools-scm-v9.3.0`, `vcs-versioning-v0.2.0`
✅ **Monorepo support** - Release one or both projects
✅ **Reusable** - Other projects can use the workflows
✅ **Auditable** - Full history in PRs and tags
✅ **Fail fast** - No fallbacks; workflows fail if required data is missing

## Architecture Highlights

```
Changelog Fragments
       ↓
Version Scheme (single source of truth)
       ↓
Development Builds ← version_from_fragments() → Release Workflow
       ↓                                              ↓
   9.3.0.dev5                                    9.3.0
                                                   ↓
                                              PyPI Upload
```

## Tag Format

Tags use project prefixes with dashes:
- `setuptools-scm-v9.3.0`
- `vcs-versioning-v0.2.0`

This enables:
- Monorepo support (different projects can have different versions)
- Controlled releases (tag prefix filters which package uploads)
- Clear git history (`git tag -l "setuptools-scm-*"`)

## Next Steps

1. Install dependencies: `uv sync --all-packages --group release`
2. Test version scheme: See TESTING.md
3. Create a test fragment and verify version calculation
4. Try a dry-run of towncrier: `uv run towncrier build --draft`

## Questions?

- See [CONTRIBUTING.md](./CONTRIBUTING.md) for contributor guide
- See [TESTING.md](./TESTING.md) for testing instructions
- See [.github/workflows/README.md](.github/workflows/README.md) for reusable workflow docs

