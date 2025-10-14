#!/usr/bin/env python3
"""Unified release proposal script for setuptools-scm monorepo."""

import os
import subprocess
import sys
from pathlib import Path

from github import Github
from github.Repository import Repository

from vcs_versioning import get_version
from vcs_versioning._config import Configuration


def find_fragments(project_dir: Path) -> list[Path]:
    """Find changelog fragments in a project directory."""
    changelog_dir = project_dir / "changelog.d"

    if not changelog_dir.exists():
        return []

    fragments = []
    for entry in changelog_dir.iterdir():
        if not entry.is_file():
            continue

        # Skip template, README, and .gitkeep files
        if entry.name in ("template.md", "README.md", ".gitkeep"):
            continue

        # Fragment naming: {number}.{type}.md
        parts = entry.name.split(".")
        if len(parts) >= 2 and entry.suffix == ".md":
            fragments.append(entry)

    return fragments


def get_next_version(project_dir: Path, repo_root: Path) -> str | None:
    """Get the next version for a project using vcs-versioning API."""
    try:
        config = Configuration(
            root=str(repo_root),
            version_scheme="towncrier-fragments",
            local_scheme="no-local-version",
        )
        
        version = get_version(config)
        
        # Extract just the public version (X.Y.Z)
        if hasattr(version, "public"):
            return str(version.public)
        else:
            return str(version).split("+")[0]  # Remove local part if present

    except Exception as e:
        print(f"Error determining version: {e}", file=sys.stderr)
        return None


def run_towncrier(project_dir: Path, version: str) -> bool:
    """Run towncrier build for a project."""
    try:
        result = subprocess.run(
            ["uv", "run", "towncrier", "build", "--version", version, "--yes"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print(f"Towncrier failed: {result.stderr}", file=sys.stderr)
            return False

        return True

    except Exception as e:
        print(f"Error running towncrier: {e}", file=sys.stderr)
        return False


def check_existing_pr(repo: Repository, source_branch: str) -> tuple[bool, int | None, str]:
    """
    Check for existing release PR.

    Returns:
        Tuple of (update_existing, pr_number, release_branch)
    """
    release_branch = f"release/{source_branch}"
    repo_owner = repo.owner.login

    try:
        pulls = repo.get_pulls(
            state="open", base="main", head=f"{repo_owner}:{release_branch}"
        )

        for pr in pulls:
            print(f"Found existing release PR #{pr.number}")
            return True, pr.number, release_branch

        print("No existing release PR found")
        return False, None, release_branch

    except Exception as e:
        print(f"Error checking for PR: {e}", file=sys.stderr)
        return False, None, release_branch


def create_or_update_pr(
    repo: Repository,
    pr_number: int | None,
    head: str,
    title: str,
    body: str,
    labels: list[str],
) -> bool:
    """Create or update a pull request."""
    try:
        if pr_number:
            # Update existing PR
            pr = repo.get_pull(pr_number)
            pr.edit(title=title, body=body)

            # Add labels if provided
            if labels:
                existing_labels = {label.name for label in pr.get_labels()}
                new_labels = [label for label in labels if label not in existing_labels]
                if new_labels:
                    pr.add_to_labels(*new_labels)

            print(f"Updated PR #{pr_number}")
        else:
            # Create new PR
            pr = repo.create_pull(title=title, body=body, head=head, base="main")

            # Add labels if provided
            if labels:
                pr.add_to_labels(*labels)

            print(f"Created new release PR #{pr.number}")

        return True

    except Exception as e:
        print(f"Error creating/updating PR: {e}", file=sys.stderr)
        return False


def main() -> None:
    # Get environment variables
    token = os.environ.get("GITHUB_TOKEN")
    repo_name = os.environ.get("GITHUB_REPOSITORY")
    source_branch = os.environ.get("GITHUB_REF_NAME")

    if not token:
        print("ERROR: GITHUB_TOKEN environment variable not set", file=sys.stderr)
        sys.exit(1)

    if not repo_name:
        print("ERROR: GITHUB_REPOSITORY environment variable not set", file=sys.stderr)
        sys.exit(1)

    if not source_branch:
        print("ERROR: GITHUB_REF_NAME environment variable not set", file=sys.stderr)
        sys.exit(1)

    # Initialize GitHub API
    gh = Github(token)
    repo = gh.get_repo(repo_name)

    # Check for existing PR
    update_existing, existing_pr_number, release_branch = check_existing_pr(
        repo, source_branch
    )

    repo_root = Path.cwd()
    projects = {
        "setuptools-scm": repo_root / "setuptools-scm",
        "vcs-versioning": repo_root / "vcs-versioning",
    }

    # Detect which projects have fragments
    to_release = {}
    for project_name, project_path in projects.items():
        fragments = find_fragments(project_path)
        to_release[project_name] = len(fragments) > 0

        if to_release[project_name]:
            print(f"Found {len(fragments)} fragment(s) for {project_name}")
        else:
            print(f"No fragments found for {project_name}")

    # Exit if no projects have fragments
    if not any(to_release.values()):
        print("No changelog fragments found in any project, skipping release")
        sys.exit(0)

    # Prepare releases
    releases = []
    labels = []

    for project_name in ["setuptools-scm", "vcs-versioning"]:
        if not to_release[project_name]:
            continue

        print(f"\nPreparing {project_name} release...")
        project_dir = projects[project_name]

        # Get next version
        version = get_next_version(project_dir, repo_root)
        if not version:
            print(
                f"ERROR: Failed to determine version for {project_name}",
                file=sys.stderr,
            )
            sys.exit(1)

        print(f"{project_name} next version: {version}")

        # Run towncrier
        if not run_towncrier(project_dir, version):
            print(
                f"ERROR: Towncrier build failed for {project_name}", file=sys.stderr
            )
            sys.exit(1)

        releases.append(f"{project_name} v{version}")
        labels.append(f"release:{project_name}")

    if not releases:
        print("ERROR: No releases were prepared", file=sys.stderr)
        sys.exit(1)

    releases_str = ", ".join(releases)
    print(f"\nSuccessfully prepared releases: {releases_str}")

    # Create or update PR
    title = f"Release: {releases_str}"
    body = f"""## Release Proposal

This PR prepares the following releases:
{releases_str}

**Source branch:** {source_branch}

### Changes
- Updated CHANGELOG.md with towncrier fragments
- Removed processed fragments from changelog.d/

### Review Checklist
- [ ] Changelog entries are accurate
- [ ] Version numbers are correct
- [ ] All tests pass

**Merging this PR will automatically create tags and trigger PyPI uploads.**"""

    success = create_or_update_pr(
        repo, existing_pr_number, release_branch, title, body, labels
    )

    if not success:
        sys.exit(1)

    # Output for GitHub Actions
    print(f"\nrelease_branch={release_branch}")
    print(f"releases={releases_str}")
    print(f"labels={','.join(labels)}")


if __name__ == "__main__":
    main()

