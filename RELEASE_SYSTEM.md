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

Entry point: `vcs_versioning._version_schemes._towncrier:version_from_fragments`

Tests: `vcs-versioning/testing_vcs/test_version_scheme_towncrier.py`

## Workflows

**Release Proposal** (`.github/workflows/release-proposal.yml`):
Runs on push to main/develop, runs towncrier, creates labeled PR

**Test + Release** (`.github/workflows/python-tests.yml`):
On PR merge with release labels, creates draft GitHub releases + tags,
builds and tests packages, then publishes to PyPI and GitHub (turning
drafts into published releases). Also handles CI builds and TestPyPI.

## Usage

**Contributors:** Add changelog fragment to `{project}/changelog.d/{number}.{type}.md`

**Maintainers:** Review release proposal PR, merge to create draft releases, build, test, and publish to PyPI

## Design Notes

- Version scheme is single source of truth, no custom scripts
- Manual approval via PR review
- Workflows fail explicitly if required data is missing
- Draft releases provide safety net (nothing visible until tests pass)
- vcs-versioning is always published before setuptools-scm (dependency ordering)

See [CONTRIBUTING.md](./CONTRIBUTING.md) and [TESTING.md](./TESTING.md) for details.

