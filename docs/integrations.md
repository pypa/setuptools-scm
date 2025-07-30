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


### Enforce fail on shallow repositories

ReadTheDocs may sometimes use shallow Git clones that lack the full history needed for proper version detection. You can use setuptools-scm's environment variable override system to enforce `fail_on_shallow` when building on ReadTheDocs:

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
      # Enforce fail_on_shallow for setuptools-scm
      - export SETUPTOOLS_SCM_OVERRIDES_FOR_${READTHEDOCS_PROJECT//-/_}='{scm.git.pre_parse="fail_on_shallow"}'
```

This configuration uses the `SETUPTOOLS_SCM_OVERRIDES_FOR_${NORMALIZED_DIST_NAME}` environment variable to override the `scm.git.pre_parse` setting specifically for your project when building on ReadTheDocs, forcing setuptools-scm to fail with a clear error if the repository is shallow.