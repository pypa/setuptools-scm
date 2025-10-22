#!/usr/bin/env python3
"""Unified release proposal script for setuptools-scm monorepo."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from github import Github
from github.Repository import Repository
from vcs_versioning._config import Configuration
from vcs_versioning._get_version_impl import (  # type: ignore[attr-defined]
    _format_version,
    parse_version,
)


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
        # Load configuration from project's pyproject.toml
        pyproject = project_dir / "pyproject.toml"
        config = Configuration.from_file(
            pyproject,
            root=str(repo_root),
            version_scheme="towncrier-fragments",
            local_scheme="no-local-version",
        )

        # Get the ScmVersion object
        scm_version = parse_version(config)
        if scm_version is None:
            print(f"ERROR: Could not parse version for {project_dir}", file=sys.stderr)
            return None

        # Format the version string
        version_string = _format_version(scm_version)

        # Extract just the public version (X.Y.Z)
        return version_string.split("+")[0]  # Remove local part if present

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


def check_existing_pr(repo: Repository, source_branch: str) -> tuple[str, int | None]:
    """
    Check for existing release PR.

    Returns:
        Tuple of (release_branch, pr_number)
    """
    release_branch = f"release/{source_branch}"
    repo_owner = repo.owner.login

    try:
        pulls = repo.get_pulls(
            state="open", base="main", head=f"{repo_owner}:{release_branch}"
        )

        for pr in pulls:
            print(f"Found existing release PR #{pr.number}")
            return release_branch, pr.number

        print("No existing release PR found, will create new")
        return release_branch, None

    except Exception as e:
        print(f"Error checking for PR: {e}", file=sys.stderr)
        return release_branch, None


def main() -> None:
    parser = argparse.ArgumentParser(description="Create release proposal")
    parser.add_argument(
        "--event",
        required=True,
        help="GitHub event type (push or pull_request)",
    )
    parser.add_argument(
        "--branch",
        required=True,
        help="Source branch name",
    )
    args = parser.parse_args()

    # Get environment variables
    token = os.environ.get("GITHUB_TOKEN")
    repo_name = os.environ.get("GITHUB_REPOSITORY")
    source_branch = args.branch
    is_pr = args.event == "pull_request"

    if not token:
        print("ERROR: GITHUB_TOKEN environment variable not set", file=sys.stderr)
        sys.exit(1)

    if not repo_name:
        print("ERROR: GITHUB_REPOSITORY environment variable not set", file=sys.stderr)
        sys.exit(1)

    # Initialize GitHub API
    gh = Github(token)
    repo = gh.get_repo(repo_name)

    # Check for existing PR (skip for pull_request events)
    if not is_pr:
        release_branch, existing_pr_number = check_existing_pr(repo, source_branch)
    else:
        release_branch = f"release/{source_branch}"
        existing_pr_number = None
        print(f"[PR VALIDATION MODE] Validating release for branch: {source_branch}")

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

        # Write GitHub Step Summary
        github_summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if github_summary:
            with open(github_summary, "a") as f:
                f.write("## Release Proposal\n\n")
                f.write("ℹ️ No changelog fragments to process\n")

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
            print(f"ERROR: Towncrier build failed for {project_name}", file=sys.stderr)
            sys.exit(1)

        releases.append(f"{project_name} v{version}")
        labels.append(f"release:{project_name}")

    if not releases:
        print("ERROR: No releases were prepared", file=sys.stderr)
        sys.exit(1)

    releases_str = ", ".join(releases)
    print(f"\nSuccessfully prepared releases: {releases_str}")

    # Write GitHub Actions outputs
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"release_branch={release_branch}\n")
            f.write(f"releases={releases_str}\n")
            f.write(f"labels={','.join(labels)}\n")

    # Prepare PR content for workflow to use
    pr_title = f"Release: {releases_str}"
    pr_body = f"""## Release Proposal

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

    # Write outputs for workflow
    if github_output:
        with open(github_output, "a") as f:
            # Write PR metadata (multiline strings need special encoding)
            f.write(f"pr_title={pr_title}\n")
            # For multiline, use GitHub Actions multiline syntax
            f.write(f"pr_body<<EOF\n{pr_body}\nEOF\n")
            # Check if PR exists
            if not is_pr:
                f.write(f"pr_exists={'true' if existing_pr_number else 'false'}\n")
                f.write(f"pr_number={existing_pr_number or ''}\n")

    # Write GitHub Step Summary
    github_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if github_summary:
        with open(github_summary, "a") as f:
            if is_pr:
                f.write("## Release Proposal Validation\n\n")
                f.write("✅ **Status:** Validated successfully\n\n")
                f.write(f"**Planned Releases:** {releases_str}\n")
            else:
                f.write("## Release Proposal\n\n")
                f.write(f"**Releases:** {releases_str}\n")

    # For PR validation, we're done
    if is_pr:
        print(f"\n[PR VALIDATION] Release validation successful: {releases_str}")
        return

    # For push events, output success but don't create PR yet
    # (workflow will create PR after pushing the branch)
    print(f"\n[PUSH] Release preparation complete: {releases_str}")
    print("[PUSH] Workflow will commit, push branch, and create/update PR")


if __name__ == "__main__":
    main()
