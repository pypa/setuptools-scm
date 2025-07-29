# Integrations

## ReadTheDocs

### Avoid having a dirty Git index

When building documentation on ReadTheDocs, file changes during the build process can cause setuptools-scm to detect a "dirty" working directory.

To avoid this issue, ReadTheDocs recommends using build customization to clean the Git state after checkout:

```yaml title=".readthedocs.yaml"
version: 2
build:
  os: "ubuntu-22.04"
  tools:
    python: "3.10"
  jobs:
    post_checkout:
      # Avoid setuptools-scm dirty Git index issues
      - git reset --hard HEAD
      - git clean -fdx
```

This ensures a clean Git working directory before setuptools-scm detects the version, preventing unwanted local version components.

Reference: [ReadTheDocs Build Customization - Avoid having a dirty Git index](https://docs.readthedocs.com/platform/stable/build-customization.html#avoid-having-a-dirty-git-index)