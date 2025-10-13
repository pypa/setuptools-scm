# vcs-versioning Tests

## Directory Name

This directory is named `testingB` instead of `testing` to avoid a pytest conftest path conflict.

### The Issue

When running tests from both `setuptools_scm` and `vcs-versioning` together:
```bash
uv run pytest -n12 testing/ nextgen/vcs-versioning/testing/
```

Pytest encounters an import path mismatch error:
```
ImportError while loading conftest '/var/home/ronny/Projects/pypa/setuptools_scm/nextgen/vcs-versioning/testing/conftest.py'.
_pytest.pathlib.ImportPathMismatchError: ('testing.conftest', '/var/home/ronny/Projects/pypa/setuptools_scm/testing/conftest.py', PosixPath('/var/home/ronny/Projects/pypa/setuptools_scm/nextgen/vcs-versioning/testing/conftest.py'))
```

This occurs because pytest cannot distinguish between two `testing/conftest.py` files at different locations with the same relative import path.

### Solution

By naming this directory `testingB`, we avoid the path conflict while keeping it clear that this contains tests for the vcs-versioning package.

## Running Tests

Run vcs-versioning tests only:
```bash
uv run pytest nextgen/vcs-versioning/testingB/
```

Run both test suites separately:
```bash
uv run pytest testing/              # setuptools_scm tests
uv run pytest nextgen/vcs-versioning/testingB/  # vcs-versioning tests
```

