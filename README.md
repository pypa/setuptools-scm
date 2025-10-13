# setuptools-scm Monorepo

This is the monorepo for the setuptools-scm ecosystem, containing two main projects:

## Projects

### [setuptools-scm](./setuptools-scm/)

The main package that extracts Python package versions from Git or Mercurial metadata and provides setuptools integration.

**[Read setuptools-scm documentation →](./setuptools-scm/README.md)**

### [vcs-versioning](./vcs-versioning/)

Core VCS versioning functionality extracted as a standalone library that can be used independently of setuptools.

**[Read vcs-versioning documentation →](./vcs-versioning/README.md)**

## Development

This workspace uses [uv](https://github.com/astral-sh/uv) for dependency management.

### Running Tests

```bash
# Run all tests
uv run pytest -n12

# Run tests for setuptools-scm only
uv run pytest setuptools-scm/testing_scm -n12

# Run tests for vcs-versioning only
uv run pytest vcs-versioning/testing_vcs -n12
```

### Building Documentation

Documentation is shared across projects:

```bash
uv run mkdocs serve
```

## Links

- **Documentation**: https://setuptools-scm.readthedocs.io/
- **Repository**: https://github.com/pypa/setuptools-scm/
- **Issues**: https://github.com/pypa/setuptools-scm/issues

## License

Both projects are distributed under the terms of the MIT license.

