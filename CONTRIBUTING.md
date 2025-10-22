# Contributing to setuptools-scm and vcs-versioning

Thank you for contributing! This document explains the development workflow, including how to add changelog entries and create releases.

## Development Setup

This is a monorepo containing two packages:
- `setuptools-scm/` - Setuptools integration for version management
- `vcs-versioning/` - Core VCS version detection and schemes

### Installation

```bash
# Install all dependencies
uv sync --all-packages --all-groups

# Run tests
uv run pytest -n12

# Run tests for specific package
uv run pytest setuptools-scm/testing_scm/ -n12
uv run pytest vcs-versioning/testing_vcs/ -n12
```

## Changelog Fragments

We use [towncrier](https://towncrier.readthedocs.io/) to manage changelog entries. This ensures that changelog entries are added alongside code changes and reduces merge conflicts.

### Adding a Changelog Fragment

When you make a change that should be noted in the changelog, create a fragment file in the appropriate project's `changelog.d/` directory:

**For setuptools-scm changes:**
```bash
# Create a fragment file
echo "Your changelog entry here" > setuptools-scm/changelog.d/123.feature.md
```

**For vcs-versioning changes:**
```bash
# Create a fragment file
echo "Your changelog entry here" > vcs-versioning/changelog.d/456.bugfix.md
```

### Fragment Naming Convention

Fragments follow the naming pattern: `{number}.{type}.md`

- **number**: Usually the GitHub issue or PR number (or any unique identifier)
- **type**: One of the types below
- **extension**: Always `.md`

### Fragment Types

The fragment type determines the version bump:

| Type | Description | Version Bump | Example |
|------|-------------|--------------|---------|
| `feature` | New features or enhancements | **Minor** (0.X.0) | `123.feature.md` |
| `bugfix` | Bug fixes | **Patch** (0.0.X) | `456.bugfix.md` |
| `deprecation` | Deprecation notices | **Minor** (0.X.0) | `789.deprecation.md` |
| `removal` | Breaking changes/removed features | **Major** (X.0.0) | `321.removal.md` |
| `doc` | Documentation improvements | **Patch** (0.0.X) | `654.doc.md` |
| `misc` | Internal changes, refactoring | **Patch** (0.0.X) | `987.misc.md` |

### Fragment Content

Keep fragments concise and user-focused. Do not include issue numbers in the content (they're added automatically).

**Good:**
```markdown
Add support for custom version schemes via plugin system
```

**Bad:**
```markdown
Fix #123: Added support for custom version schemes via plugin system in the configuration
```

## Version Scheme Integration

The `towncrier-fragments` version scheme automatically determines version bumps based on changelog fragments. During development builds, the version will reflect the next release version:

```bash
# If you have a feature fragment, version might be:
9.3.0.dev5+g1234567

# If you only have bugfix fragments:
9.2.2.dev5+g1234567
```

This ensures that the version you see during development will be the actual release version.

## Release Process

Releases are managed through GitHub Actions workflows with manual approval.

### 1. Create a Release Proposal

Maintainers trigger the release workflow manually:

1. Go to **Actions** → **Create Release Proposal**
2. Select which projects to release:
   - ☑ Release setuptools-scm
   - ☑ Release vcs-versioning
3. Click **Run workflow**

The workflow will:
- Analyze changelog fragments in each project
- Determine the version bump (major/minor/patch) based on fragment types
- Query the `towncrier-fragments` version scheme for the next version
- Run `towncrier build` to update the CHANGELOG.md
- Create a release PR with the changes
- Label the PR with `release:setuptools-scm` and/or `release:vcs-versioning`

### 2. Review and Approve

Review the release PR:
- Check that the changelog entries are accurate
- Verify the version numbers are correct
- Ensure all tests pass

### 3. Merge to Release

When you merge the PR to `main`:
- The merge triggers the tag creation workflow automatically
- Tags are created with the project prefix:
  - `setuptools-scm-v9.3.0`
  - `vcs-versioning-v0.2.0`
- GitHub releases are created with changelog excerpts
- Tag pushes trigger the PyPI upload workflow
- Only the package(s) matching the tag prefix are uploaded to PyPI

## Workflow Architecture

The release system is designed to be reusable by other projects:

### Key Components

1. **Version Scheme** (`vcs_versioning._version_schemes._towncrier`)
   - Analyzes fragments to determine version bump
   - Used by both development builds and release workflow
   - No version calculation logic in scripts - single source of truth

2. **Release Proposal Workflow** (`.github/workflows/release-proposal.yml`)
   - Manual trigger with project selection
   - Uses `vcs-versioning` CLI to query version scheme
   - Runs `towncrier build` with the determined version
   - Creates labeled PR

3. **Tag Creation Workflow** (`.github/workflows/create-release-tags.yml`)
   - Triggered by PR merge with release labels
   - Creates project-prefixed tags
   - Creates GitHub releases

4. **Upload Workflow** (`.github/workflows/python-tests.yml`)
   - Triggered by tag push (filtered by tag prefix)
   - Uploads only matching package to PyPI

### Benefits

- ✅ Version determination is consistent (version scheme is single source of truth)
- ✅ Manual approval via familiar PR review process
- ✅ Atomic releases tied to merge commits
- ✅ Project-specific tags prevent accidental releases
- ✅ Can release one or both projects in a single PR
- ✅ Fully auditable release process
- ✅ Reusable workflows for other projects

## Testing Locally

You can test the version scheme locally:

```bash
# See what version would be generated
cd setuptools-scm
uv run python -m vcs_versioning --root .. --version-scheme towncrier-fragments

# Test towncrier build (dry-run)
cd setuptools-scm
uv run towncrier build --version 9.3.0 --draft
```

## Questions?

- Check [TESTING.md](./TESTING.md) for testing guidelines
- Open an issue for bugs or feature requests
- Ask in discussions for general questions

