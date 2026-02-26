# Reusable Workflows for Towncrier-based Releases

This directory contains reusable GitHub Actions workflows that other projects can use to implement the same towncrier-based release process.

## Available Reusable Workflows

### `reusable-towncrier-release.yml`

Determines the next version using the `towncrier-fragments` version scheme and builds the changelog.

**Inputs:**
- `project_name` (required): Name of the project (used for labeling and tag prefix)
- `project_directory` (required): Directory containing the project (relative to repository root)

**Outputs:**
- `version`: The determined next version
- `has_fragments`: Whether fragments were found

**Behavior:**
- ✅ Strict validation - workflow fails if changelog fragments or version data is missing
- ✅ No fallback values - ensures data integrity for releases
- ✅ Clear error messages to guide troubleshooting

**Example usage:**

```yaml
jobs:
  determine-version:
    uses: pypa/setuptools-scm/.github/workflows/reusable-towncrier-release.yml@main
    with:
      project_name: my-project
      project_directory: ./
```

## Using These Workflows in Your Project

### Prerequisites

1. **Add vcs-versioning dependency** to your project
2. **Configure towncrier** in your `pyproject.toml`:

```toml
[tool.towncrier]
directory = "changelog.d"
filename = "CHANGELOG.md"
start_string = "<!-- towncrier release notes start -->\n"
template = "changelog.d/template.md"
title_format = "## {version} ({project_date})"

[[tool.towncrier.type]]
directory = "removal"
name = "Removed"
showcontent = true

[[tool.towncrier.type]]
directory = "feature"
name = "Added"
showcontent = true

[[tool.towncrier.type]]
directory = "bugfix"
name = "Fixed"
showcontent = true
```

3. **Create changelog structure**:
   - `changelog.d/` directory
   - `changelog.d/template.md` (towncrier template)
   - `CHANGELOG.md` with the start marker

4. **Configure version scheme** in your `pyproject.toml`:

```toml
[tool.setuptools_scm]
version_scheme = "towncrier-fragments"
```

The `towncrier-fragments` version scheme is provided by vcs-versioning 0.2.0+.
The reusable workflow reads the scheme from the project's `pyproject.toml` via the CLI.

### Complete Example Workflow

```yaml
name: Create Release

on:
  workflow_dispatch:
    inputs:
      create_release:
        description: 'Create release'
        required: true
        type: boolean
        default: false

permissions:
  contents: write
  pull-requests: write

jobs:
  determine-version:
    uses: pypa/setuptools-scm/.github/workflows/reusable-towncrier-release.yml@main
    with:
      project_name: my-project
      project_directory: ./

  create-release-pr:
    needs: determine-version
    if: needs.determine-version.outputs.has_fragments == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5

      - name: Download changelog artifacts
        uses: actions/download-artifact@v4
        with:
          name: changelog-my-project

      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v7
        with:
          commit-message: "Release v${{ needs.determine-version.outputs.version }}"
          branch: release-${{ needs.determine-version.outputs.version }}
          title: "Release v${{ needs.determine-version.outputs.version }}"
          labels: release:my-project
          body: |
            Automated release PR for version ${{ needs.determine-version.outputs.version }}
```

## Architecture

The workflow system is designed with these principles:

1. **Version scheme is single source of truth** - No version calculation in scripts
2. **Reusable components** - Other projects can use the same workflows
3. **Manual approval** - Release PRs must be reviewed and merged
4. **Project-prefixed tags** - Enable monorepo releases (`project-vX.Y.Z`)
5. **Automated but controlled** - Automation with human approval gates
6. **Fail fast** - No fallback values; workflows fail explicitly if required data is missing
7. **No custom scripts** - Uses PR title parsing and built-in tools only

## Version Bump Logic

The `towncrier-fragments` version scheme determines bumps based on fragment types:

| Fragment Type | Version Bump | Example |
|---------------|--------------|---------|
| `removal` | Major (X.0.0) | Breaking changes |
| `feature`, `deprecation` | Minor (0.X.0) | New features |
| `bugfix`, `doc`, `misc` | Patch (0.0.X) | Bug fixes |

## Support

For issues or questions about these workflows:
- Open an issue at https://github.com/pypa/setuptools-scm/issues
- See full documentation in [CONTRIBUTING.md](../../CONTRIBUTING.md)

