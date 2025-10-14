# Release System

Towncrier-based release system for the setuptools-scm monorepo.

## Components

- `towncrier-fragments` version scheme: Determines version bumps from changelog fragment types
- `changelog.d/` directories per project with fragment templates
- GitHub workflows for release proposals and tag creation
- Project-prefixed tags: `setuptools-scm-vX.Y.Z`, `vcs-versioning-vX.Y.Z`

## Version Scheme

Fragment types determine version bumps:
- `removal` → major bump
- `feature`, `deprecation` → minor bump
- `bugfix`, `doc`, `misc` → patch bump

Entry point: `vcs_versioning._version_schemes_towncrier:version_from_fragments`

Tests: `vcs-versioning/testing_vcs/test_version_scheme_towncrier.py`

## Workflows

**Release Proposal** (`.github/workflows/release-proposal.yml`):
Manual trigger, runs towncrier, creates labeled PR

**Tag Creation** (`.github/workflows/create-release-tags.yml`):
On PR merge, creates tags from PR title, triggers PyPI upload

**Modified Upload** (`.github/workflows/python-tests.yml`):
Split per-project upload jobs filtered by tag prefix

## Usage

**Contributors:** Add changelog fragment to `{project}/changelog.d/{number}.{type}.md`

**Maintainers:** Trigger release proposal workflow, review PR, merge to create tags and upload to PyPI

## Design Notes

- Version scheme is single source of truth, no custom scripts
- Manual approval via PR review
- Workflows fail explicitly if required data is missing
- Tag prefix filtering controls package uploads

See [CONTRIBUTING.md](./CONTRIBUTING.md) and [TESTING.md](./TESTING.md) for details.

